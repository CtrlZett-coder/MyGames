/**
 * Space Shooter — Multiplayer Server
 * Socket.io-based co-op relay server.
 *
 * Events (client → server):
 *   create_room  {callsign, uid}        → room_created / room_err
 *   join_room    {code, callsign, uid}  → room_joined  / room_err
 *   start_game   (host only)            → game_start (broadcast)
 *   ps           player state           relayed to others in room
 *   bf           bullet fired           relayed to others in room
 *   es           enemy state (host)     relayed to non-hosts
 *   eh           enemy hit (non-host)   forwarded to host
 *   ek           enemy killed (host)    broadcast to room
 *   leave_room                          removes player, notifies room
 *
 * Events (server → client):
 *   room_created {code, players}
 *   room_joined  {code, players, isHost}
 *   room_err     'message'
 *   player_joined player
 *   player_left  {id}
 *   new_host     {id}
 *   game_start   {players}
 *   ps / bf / es / eh / ek  (relayed as above)
 */

'use strict';
const http = require('http');
const { Server } = require('socket.io');

const httpServer = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Space Shooter Multiplayer Server\n');
});

const io = new Server(httpServer, {
  cors: { origin: '*', methods: ['GET', 'POST'] },
  pingTimeout: 20000,
  pingInterval: 10000,
});

// rooms[code] = { host: socketId, started: bool, players: { socketId: playerInfo } }
const rooms = {};

function genCode() {
  let code;
  do { code = Math.random().toString(36).slice(2, 6).toUpperCase(); }
  while (rooms[code]);
  return code;
}

function roomPlayerList(room) {
  // Return a plain object safe to JSON-send
  const out = {};
  for (const [id, p] of Object.entries(room.players)) out[id] = { ...p };
  return out;
}

function nextSlot(room) {
  const used = new Set(Object.values(room.players).map(p => p.slot));
  for (let i = 1; i <= 3; i++) if (!used.has(i)) return i;
  return null;
}

io.on('connection', socket => {
  let code = null; // room this socket is in

  // ── Create room ──────────────────────────────────────────────────────────────
  socket.on('create_room', ({ callsign = 'Pilot', uid = '' } = {}) => {
    if (code) return; // already in a room
    code = genCode();
    rooms[code] = {
      host: socket.id,
      started: false,
      players: {
        [socket.id]: { id: socket.id, callsign, uid, slot: 0 }
      }
    };
    socket.join(code);
    socket.emit('room_created', { code, players: roomPlayerList(rooms[code]) });
    console.log(`Room ${code} created by ${callsign}`);
  });

  // ── Join room ─────────────────────────────────────────────────────────────────
  socket.on('join_room', ({ code: rc = '', callsign = 'Pilot', uid = '' } = {}) => {
    if (code) return;
    const c = rc.toUpperCase().trim();
    const room = rooms[c];
    if (!room) { socket.emit('room_err', 'Room not found'); return; }
    if (room.started) { socket.emit('room_err', 'Game already started'); return; }
    const slot = nextSlot(room);
    if (slot === null) { socket.emit('room_err', 'Room is full (max 4 players)'); return; }
    code = c;
    room.players[socket.id] = { id: socket.id, callsign, uid, slot };
    socket.join(c);
    socket.emit('room_joined', { code: c, players: roomPlayerList(room), isHost: false });
    socket.to(c).emit('player_joined', { ...room.players[socket.id] });
    console.log(`${callsign} joined room ${c} (slot ${slot})`);
  });

  // ── Start game (host only) ────────────────────────────────────────────────────
  socket.on('start_game', () => {
    const room = rooms[code];
    if (!room || room.host !== socket.id) return;
    room.started = true;
    io.to(code).emit('game_start', { players: roomPlayerList(room) });
    console.log(`Room ${code} game started (${Object.keys(room.players).length} players)`);
  });

  // ── In-game relay: player state ───────────────────────────────────────────────
  socket.on('ps', state => {
    if (code) socket.to(code).emit('ps', { id: socket.id, ...state });
  });

  // ── In-game relay: bullet fired ───────────────────────────────────────────────
  socket.on('bf', bullet => {
    if (code) socket.to(code).emit('bf', { ownerId: socket.id, ...bullet });
  });

  // ── In-game relay: enemy state (host → clients) ───────────────────────────────
  socket.on('es', enemies => {
    const room = rooms[code];
    if (!room || room.host !== socket.id) return;
    socket.to(code).emit('es', enemies);
  });

  // ── In-game relay: enemy hit (client → host) ──────────────────────────────────
  socket.on('eh', data => {
    const room = rooms[code];
    if (!room || socket.id === room.host) return;
    io.to(room.host).emit('eh', { ...data, from: socket.id });
  });

  // ── In-game relay: enemy killed (host → all) ──────────────────────────────────
  socket.on('ek', data => {
    const room = rooms[code];
    if (!room || room.host !== socket.id) return;
    socket.to(code).emit('ek', data);
  });

  // ── Leave room ────────────────────────────────────────────────────────────────
  socket.on('leave_room', () => _leave());

  // ── Disconnect ────────────────────────────────────────────────────────────────
  socket.on('disconnect', () => _leave());

  function _leave() {
    if (!code || !rooms[code]) { code = null; return; }
    const room = rooms[code];
    delete room.players[socket.id];
    socket.to(code).emit('player_left', { id: socket.id });
    socket.leave(code);

    if (Object.keys(room.players).length === 0) {
      delete rooms[code];
      console.log(`Room ${code} deleted (empty)`);
    } else if (room.host === socket.id) {
      // Transfer host to the next player
      room.host = Object.keys(room.players)[0];
      io.to(code).emit('new_host', { id: room.host });
      console.log(`Room ${code} host transferred to ${room.players[room.host].callsign}`);
    }
    code = null;
  }
});

const PORT = process.env.PORT || 3001;
httpServer.listen(PORT, () => {
  console.log(`Space Shooter multiplayer server running on port ${PORT}`);
});
