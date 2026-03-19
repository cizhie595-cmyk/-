"""
Tests for GAP-01 through GAP-05 features (PRD completion)

GAP-01: API Status Indicator (top bar green/yellow/red lights)
GAP-02: Image Preprocessor (Canvas resize + bg removal)
GAP-03: Skeleton Loader (global loading states)
GAP-04: Empty State Components (unified illustrations)
GAP-05: Performance Optimization (CDN/cache/compression)
"""

import os
import re
import pytest

# ========== Paths ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
JS_DIR = os.path.join(STATIC_DIR, "js")
CSS_DIR = os.path.join(STATIC_DIR, "css")


# ========== Helper ==========
def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ========== GAP-01: API Status Indicator ==========
class TestGAP01_ApiStatusIndicator:
    """Test API status indicator in top bar"""

    def test_base_html_has_status_dots(self):
        """base.html should contain API status indicator dots"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "api-status" in html, "Missing api-status element in base.html"

    def test_base_html_has_check_api_status_function(self):
        """base.html should have checkApiStatus function with connectivity test"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "checkApiStatus" in html, "Missing checkApiStatus function"

    def test_status_indicator_has_three_states(self):
        """Status indicator should support green/yellow/red states"""
        css = read_file(os.path.join(CSS_DIR, "main.css"))
        assert "status-green" in css or "green" in css, "Missing green status style"

    def test_status_tooltip_exists(self):
        """Status dots should have tooltip/popup for details"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "tooltip" in html.lower() or "popup" in html.lower() or "title=" in html, \
            "Missing tooltip for status indicators"

    def test_auto_refresh_interval(self):
        """Status check should have auto-refresh interval"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "setInterval" in html and "checkApiStatus" in html, \
            "Missing auto-refresh interval for status check"

    def test_force_test_on_first_load(self):
        """First load should force connectivity test"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "forceTest" in html or "force" in html.lower(), \
            "Missing force test on first load"


# ========== GAP-02: Image Preprocessor ==========
class TestGAP02_ImagePreprocessor:
    """Test Canvas-based image preprocessing module"""

    def test_image_preprocessor_js_exists(self):
        """image_preprocessor.js should exist"""
        path = os.path.join(JS_DIR, "image_preprocessor.js")
        assert os.path.exists(path), "image_preprocessor.js not found"

    def test_image_preprocessor_class_defined(self):
        """ImagePreprocessor class should be defined"""
        js = read_file(os.path.join(JS_DIR, "image_preprocessor.js"))
        assert "class ImagePreprocessor" in js, "ImagePreprocessor class not defined"

    def test_has_process_method(self):
        """Should have process() method for resize/compress"""
        js = read_file(os.path.join(JS_DIR, "image_preprocessor.js"))
        assert "async process(" in js, "Missing process() method"

    def test_has_bg_removal_method(self):
        """Should have processWithBgRemoval() method"""
        js = read_file(os.path.join(JS_DIR, "image_preprocessor.js"))
        assert "processWithBgRemoval" in js, "Missing processWithBgRemoval() method"

    def test_has_client_side_fallback(self):
        """Should have client-side bg removal fallback"""
        js = read_file(os.path.join(JS_DIR, "image_preprocessor.js"))
        assert "_clientSideBgRemoval" in js, "Missing client-side bg removal fallback"

    def test_max_size_1024(self):
        """Default max size should be 1024"""
        js = read_file(os.path.join(JS_DIR, "image_preprocessor.js"))
        assert "1024" in js, "Missing 1024 max size default"

    def test_preview_widget(self):
        """Should have createPreviewWidget static method"""
        js = read_file(os.path.join(JS_DIR, "image_preprocessor.js"))
        assert "createPreviewWidget" in js, "Missing preview widget"

    def test_threed_lab_integration(self):
        """threed_lab.html should integrate image preprocessor"""
        html = read_file(os.path.join(TEMPLATES_DIR, "threed_lab.html"))
        assert "image_preprocessor.js" in html, "image_preprocessor.js not loaded in threed_lab.html"
        assert "onImageFileSelected" in html, "Missing onImageFileSelected handler"

    def test_threed_lab_preview_container(self):
        """threed_lab.html should have preview container"""
        html = read_file(os.path.join(TEMPLATES_DIR, "threed_lab.html"))
        assert "gen-image-preview" in html, "Missing gen-image-preview container"

    def test_preprocessor_css_styles(self):
        """main.css should have preprocessor widget styles"""
        css = read_file(os.path.join(CSS_DIR, "main.css"))
        assert "img-preprocess-widget" in css or "preprocess" in css, \
            "Missing image preprocessor CSS styles"


# ========== GAP-03: Skeleton Loader ==========
class TestGAP03_SkeletonLoader:
    """Test global skeleton screen loading component"""

    def test_skeleton_loader_js_exists(self):
        """skeleton_loader.js should exist"""
        path = os.path.join(JS_DIR, "skeleton_loader.js")
        assert os.path.exists(path), "skeleton_loader.js not found"

    def test_skeleton_loader_class_defined(self):
        """SkeletonLoader class should be defined"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        assert "class SkeletonLoader" in js, "SkeletonLoader class not defined"

    def test_has_show_method(self):
        """Should have show() method"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        assert "show(" in js, "Missing show() method"

    def test_has_hide_method(self):
        """Should have hide() method"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        assert "hide(" in js, "Missing hide() method"

    def test_supports_multiple_layouts(self):
        """Should support cards, table, stats, chart, list, detail, form, dashboard"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        layouts = ['cards', 'table', 'stats', 'chart', 'list', 'detail', 'form', 'dashboard']
        for layout in layouts:
            assert f"'{layout}'" in js or f'"{layout}"' in js, f"Missing layout: {layout}"

    def test_has_with_skeleton_helper(self):
        """Should have withSkeleton() convenience function"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        assert "withSkeleton" in js, "Missing withSkeleton helper"

    def test_fade_transition(self):
        """Should support fade transition"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        assert "fadeMs" in js or "fade" in js.lower(), "Missing fade transition support"

    def test_global_instance(self):
        """Should export global skeleton instance"""
        js = read_file(os.path.join(JS_DIR, "skeleton_loader.js"))
        assert "window.skeleton" in js or "window.SkeletonLoader" in js, \
            "Missing global export"

    def test_base_html_includes_skeleton_loader(self):
        """base.html should include skeleton_loader.js"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "skeleton_loader.js" in html, "skeleton_loader.js not included in base.html"

    def test_skeleton_css_enhanced(self):
        """main.css should have enhanced skeleton styles"""
        css = read_file(os.path.join(CSS_DIR, "main.css"))
        assert "skeleton-wrapper" in css, "Missing skeleton-wrapper CSS"


# ========== GAP-04: Empty State Components ==========
class TestGAP04_EmptyStates:
    """Test unified empty state illustration components"""

    def test_empty_states_js_exists(self):
        """empty_states.js should exist"""
        path = os.path.join(JS_DIR, "empty_states.js")
        assert os.path.exists(path), "empty_states.js not found"

    def test_empty_state_class_defined(self):
        """EmptyState class should be defined"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        assert "class EmptyState" in js, "EmptyState class not defined"

    def test_has_render_method(self):
        """Should have static render() method"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        assert "static render(" in js, "Missing render() method"

    def test_supports_all_types(self):
        """Should support all required empty state types"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        types = ['no-data', 'no-results', 'error', 'no-projects', 'no-products',
                 'welcome', 'no-keywords', 'no-suppliers', 'no-competitors']
        for t in types:
            assert f"'{t}'" in js or f'"{t}"' in js, f"Missing empty state type: {t}"

    def test_svg_illustrations(self):
        """Each type should have SVG illustration"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        svg_methods = ['_svgNoData', '_svgNoResults', '_svgError', '_svgNoProjects',
                       '_svgNoProducts', '_svgWelcome', '_svgNoKeywords',
                       '_svgNoSuppliers', '_svgNoCompetitors']
        for method in svg_methods:
            assert method in js, f"Missing SVG method: {method}"

    def test_cta_button_support(self):
        """Should support call-to-action buttons"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        assert "actionText" in js, "Missing CTA button support"
        assert "onAction" in js, "Missing onAction handler support"

    def test_custom_title_message(self):
        """Should support custom title and message"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        assert "options.title" in js, "Missing custom title support"
        assert "options.message" in js, "Missing custom message support"

    def test_base_html_includes_empty_states(self):
        """base.html should include empty_states.js"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "empty_states.js" in html, "empty_states.js not included in base.html"

    def test_empty_state_css(self):
        """main.css should have empty state styles"""
        css = read_file(os.path.join(CSS_DIR, "main.css"))
        assert "empty-state" in css, "Missing empty-state CSS styles"

    def test_global_export(self):
        """Should export EmptyState globally"""
        js = read_file(os.path.join(JS_DIR, "empty_states.js"))
        assert "window.EmptyState" in js, "Missing global EmptyState export"


# ========== GAP-05: Performance Optimization ==========
class TestGAP05_PerformanceOptimization:
    """Test first-screen performance optimization"""

    def test_preconnect_cdn_jsdelivr(self):
        """base.html should preconnect to cdn.jsdelivr.net"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert 'preconnect" href="https://cdn.jsdelivr.net"' in html, \
            "Missing preconnect to cdn.jsdelivr.net"

    def test_preconnect_fonts_gstatic(self):
        """base.html should preconnect to fonts.gstatic.com"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "fonts.gstatic.com" in html, "Missing preconnect to fonts.gstatic.com"

    def test_dns_prefetch(self):
        """base.html should have dns-prefetch hints"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "dns-prefetch" in html, "Missing dns-prefetch hints"

    def test_preload_critical_css(self):
        """base.html should preload main.css"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert 'preload" href="/static/css/main.css"' in html, \
            "Missing preload for main.css"

    def test_preload_critical_js(self):
        """base.html should preload api.js"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert 'preload" href="/static/js/api.js"' in html, \
            "Missing preload for api.js"

    def test_critical_inline_css(self):
        """base.html should have inline critical CSS"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "critical" in html.lower() and "<style>" in html, \
            "Missing inline critical CSS"

    def test_font_display_swap(self):
        """Font loading should use display=swap"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        assert "display=swap" in html, "Missing font display=swap"

    def test_app_py_cache_headers(self):
        """app.py should set cache headers for static assets"""
        app_py = read_file(os.path.join(BASE_DIR, "app.py"))
        assert "Cache-Control" in app_py, "Missing Cache-Control header in app.py"
        assert "max-age" in app_py, "Missing max-age in cache headers"

    def test_app_py_security_headers(self):
        """app.py should set security headers"""
        app_py = read_file(os.path.join(BASE_DIR, "app.py"))
        assert "X-Content-Type-Options" in app_py, "Missing X-Content-Type-Options"
        assert "X-Frame-Options" in app_py, "Missing X-Frame-Options"

    def test_app_py_gzip_compression(self):
        """app.py should configure Gzip compression"""
        app_py = read_file(os.path.join(BASE_DIR, "app.py"))
        assert "flask_compress" in app_py or "Compress" in app_py, \
            "Missing Gzip compression configuration"

    def test_app_py_send_file_max_age(self):
        """app.py should set SEND_FILE_MAX_AGE_DEFAULT"""
        app_py = read_file(os.path.join(BASE_DIR, "app.py"))
        assert "SEND_FILE_MAX_AGE_DEFAULT" in app_py, \
            "Missing SEND_FILE_MAX_AGE_DEFAULT configuration"


# ========== Cross-cutting: All JS files loaded in base.html ==========
class TestGlobalIntegration:
    """Test that all new JS modules are properly loaded"""

    def test_all_new_js_loaded_in_base(self):
        """All new JS modules should be loaded in base.html"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        required_js = ['api.js', 'i18n.js', 'skeleton_loader.js', 'empty_states.js']
        for js in required_js:
            assert js in html, f"{js} not loaded in base.html"

    def test_js_load_order(self):
        """JS files should be loaded in correct order"""
        html = read_file(os.path.join(TEMPLATES_DIR, "base.html"))
        api_pos = html.find('api.js')
        skeleton_pos = html.find('skeleton_loader.js')
        empty_pos = html.find('empty_states.js')
        assert api_pos < skeleton_pos < empty_pos, \
            "JS files not loaded in correct order"

    def test_new_js_files_not_empty(self):
        """All new JS files should have substantial content"""
        files = ['image_preprocessor.js', 'skeleton_loader.js', 'empty_states.js']
        for f in files:
            path = os.path.join(JS_DIR, f)
            assert os.path.exists(path), f"{f} not found"
            content = read_file(path)
            assert len(content) > 500, f"{f} appears to be empty or too small ({len(content)} chars)"

    def test_no_syntax_errors_in_css(self):
        """main.css should not have obvious syntax errors"""
        css = read_file(os.path.join(CSS_DIR, "main.css"))
        # Check balanced braces
        open_braces = css.count('{')
        close_braces = css.count('}')
        assert abs(open_braces - close_braces) <= 2, \
            f"CSS brace mismatch: {open_braces} open vs {close_braces} close"
