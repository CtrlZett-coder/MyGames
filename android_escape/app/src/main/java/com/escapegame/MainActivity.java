package com.escapegame;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {

    private WebView mWebView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        mWebView = new WebView(this);

        mWebView.setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE         |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION|
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN     |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION       |
            View.SYSTEM_UI_FLAG_FULLSCREEN            |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );

        WebSettings s = mWebView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(false);

        mWebView.setWebViewClient(new WebViewClient());
        mWebView.loadUrl("file:///android_asset/game.html");

        setContentView(mWebView);
    }

    @Override
    public void onBackPressed() {
        // Swallow back-button so the game doesn't close accidentally
    }

    @Override
    protected void onResume() {
        super.onResume();
        mWebView.setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_FULLSCREEN      |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }
}
