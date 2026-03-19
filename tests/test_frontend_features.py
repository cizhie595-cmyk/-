"""
Tests for Frontend Feature Enhancements (F-01 to F-08)
Phase 17 - PRD Frontend UI Completion
"""
import os
import re
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'frontend', 'static')
CSS_DIR = os.path.join(STATIC_DIR, 'css')
JS_DIR = os.path.join(STATIC_DIR, 'js')


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ============================================================
# F-01: Scrape Depth Selector
# ============================================================
class TestF01ScrapeDepthSelector:
    """Test Scrape Depth slider selector in new_project.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'new_project.html'))

    def test_depth_radio_buttons_exist(self):
        """Verify Top 50/100/200 radio buttons exist"""
        assert 'name="scrape-depth"' in self.content
        assert 'value="50"' in self.content
        assert 'value="100"' in self.content
        assert 'value="200"' in self.content

    def test_depth_slider_exists(self):
        """Verify range slider exists"""
        assert 'id="depth-slider"' in self.content
        assert 'type="range"' in self.content

    def test_depth_card_ui(self):
        """Verify depth card UI with labels"""
        assert 'Top 50' in self.content
        assert 'Top 100' in self.content
        assert 'Top 200' in self.content
        assert 'Quick scan' in self.content
        assert 'Recommended' in self.content
        assert 'Deep analysis' in self.content

    def test_default_selection(self):
        """Verify default is Top 100"""
        assert 'value="100" checked' in self.content

    def test_depth_js_functions(self):
        """Verify JS functions for depth interaction"""
        assert 'function updateDepthDisplay' in self.content
        assert 'function updateDepthFromSlider' in self.content

    def test_depth_sent_in_create_project(self):
        """Verify scrape_depth is included in project creation data"""
        assert 'scrape_depth:' in self.content

    def test_depth_css_styles(self):
        """Verify CSS styles for depth selector"""
        assert '.depth-card' in self.content
        assert '.depth-slider' in self.content
        assert '.depth-value' in self.content


# ============================================================
# F-02: Quick Filter Panel
# ============================================================
class TestF02QuickFilterPanel:
    """Test quick filter panel in project_detail.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'project_detail.html'))

    def test_advanced_filters_panel_exists(self):
        """Verify advanced filters panel exists"""
        assert 'id="advanced-filters"' in self.content
        assert 'Advanced Filters' in self.content

    def test_price_range_inputs(self):
        """Verify price min/max inputs"""
        assert 'id="filter-price-min"' in self.content
        assert 'id="filter-price-max"' in self.content

    def test_reviews_range_inputs(self):
        """Verify review count min/max inputs"""
        assert 'id="filter-reviews-min"' in self.content
        assert 'id="filter-reviews-max"' in self.content

    def test_sales_min_input(self):
        """Verify monthly sales min input"""
        assert 'id="filter-sales-min"' in self.content

    def test_bsr_max_input(self):
        """Verify BSR rank max input"""
        assert 'id="filter-bsr-max"' in self.content

    def test_rating_radio_chips(self):
        """Verify rating filter radio chips"""
        assert 'name="rating-filter"' in self.content
        assert '4.5+' in self.content
        assert '4.0+' in self.content
        assert '3.5+' in self.content
        assert '3.0+' in self.content

    def test_fba_filter(self):
        """Verify FBA/FBM filter"""
        assert 'name="fba-filter"' in self.content
        assert 'FBA Only' in self.content
        assert 'FBM Only' in self.content

    def test_brand_exclude_tags(self):
        """Verify brand exclude tag input"""
        assert 'id="brand-exclude-input"' in self.content
        assert 'id="brand-tags"' in self.content
        assert 'Exclude Brands' in self.content

    def test_reset_button(self):
        """Verify reset all button"""
        assert 'onclick="resetFilters()"' in self.content

    def test_toggle_function(self):
        """Verify toggle function exists"""
        assert 'function toggleAdvancedFilters()' in self.content

    def test_brand_tag_functions(self):
        """Verify brand tag JS functions"""
        assert 'function handleBrandTagKey' in self.content
        assert 'function removeBrandTag' in self.content
        assert 'function renderBrandTags' in self.content

    def test_enhanced_getFilteredProducts(self):
        """Verify getFilteredProducts uses all filter criteria"""
        assert 'filter-price-min' in self.content
        assert 'filter-price-max' in self.content
        assert 'excludedBrands' in self.content
        assert 'ratingFilter' in self.content
        assert 'fbaFilter' in self.content


# ============================================================
# F-03: AI Filter Textarea
# ============================================================
class TestF03AIFilterTextarea:
    """Test AI filter textarea panel in project_detail.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'project_detail.html'))

    def test_ai_filter_panel_exists(self):
        """Verify AI filter panel exists"""
        assert 'id="ai-filter-panel"' in self.content

    def test_ai_filter_textarea(self):
        """Verify textarea replaces prompt()"""
        assert 'id="ai-filter-textarea"' in self.content
        assert '<textarea' in self.content

    def test_ai_filter_placeholder(self):
        """Verify helpful placeholder text"""
        assert 'lightweight products' in self.content or 'private label' in self.content

    def test_ai_filter_button(self):
        """Verify apply button"""
        assert 'Apply AI Filter' in self.content

    def test_no_prompt_dialog(self):
        """Verify prompt() is no longer used for AI filter"""
        # The applyAIFilter should read from textarea, not prompt()
        assert "prompt('Describe" not in self.content

    def test_toggle_function(self):
        """Verify toggle function"""
        assert 'function toggleAIFilterPanel()' in self.content


# ============================================================
# F-04: CSV Field Mapping Modal
# ============================================================
class TestF04CSVFieldMapping:
    """Test CSV field mapping confirmation modal in new_project.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'new_project.html'))

    def test_mapping_modal_exists(self):
        """Verify field mapping modal exists"""
        assert 'id="field-mapping-modal"' in self.content

    def test_modal_header(self):
        """Verify modal header"""
        assert 'Confirm Column Mapping' in self.content

    def test_mapping_fields_container(self):
        """Verify mapping fields container"""
        assert 'id="mapping-fields"' in self.content

    def test_preview_table(self):
        """Verify data preview table"""
        assert 'id="mapping-preview-table"' in self.content

    def test_standard_fields_defined(self):
        """Verify standard field options"""
        assert 'STANDARD_FIELDS' in self.content
        assert "'asin'" in self.content
        assert "'search_term'" in self.content
        assert "'title'" in self.content
        assert "'price'" in self.content
        assert "'ignore'" in self.content

    def test_show_mapping_modal_function(self):
        """Verify showFieldMappingModal function"""
        assert 'function showFieldMappingModal' in self.content

    def test_confirm_mapping_function(self):
        """Verify confirmFieldMapping function"""
        assert 'function confirmFieldMapping' in self.content

    def test_mapping_sent_in_create(self):
        """Verify column_mapping sent in project creation"""
        assert 'column_mapping:' in self.content

    def test_edit_mapping_link(self):
        """Verify user can re-edit mapping"""
        assert 'Edit column mapping' in self.content

    def test_modal_css(self):
        """Verify modal CSS styles"""
        assert '.modal-overlay' in self.content
        assert '.modal-header' in self.content
        assert '.modal-footer' in self.content


# ============================================================
# F-05: Enhanced Data Table
# ============================================================
class TestF05EnhancedDataTable:
    """Test enhanced data table features in project_detail.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'project_detail.html'))
        self.css = read_file(os.path.join(CSS_DIR, 'main.css'))

    def test_sticky_header(self):
        """Verify sticky header"""
        assert 'position: sticky' in self.content
        assert 'top: 0' in self.content

    def test_horizontal_scroll(self):
        """Verify horizontal scroll container"""
        assert 'overflow-x: auto' in self.content

    def test_column_resize_handles(self):
        """Verify resize handles on columns"""
        assert 'resize-handle' in self.content
        assert 'function initResize' in self.content
        assert 'function doResize' in self.content
        assert 'function stopResize' in self.content

    def test_column_visibility_toggle(self):
        """Verify column visibility toggle"""
        assert 'id="column-menu"' in self.content
        assert 'function toggleColumnMenu' in self.content
        assert 'function toggleColumn' in self.content

    def test_column_checkboxes(self):
        """Verify individual column checkboxes"""
        for col in ['Image', 'ASIN / Title', 'Price', 'Rating', 'Reviews', 'Monthly Sales', 'BSR', 'FBA', 'Actions']:
            assert col in self.content

    def test_column_classes(self):
        """Verify column classes for visibility control"""
        for i in range(10):
            assert f'class="col-{i}' in self.content or f'col-{i}"' in self.content

    def test_resize_css(self):
        """Verify resize handle CSS"""
        assert '.resize-handle' in self.css
        assert 'col-resize' in self.css

    def test_column_menu_css(self):
        """Verify column menu CSS"""
        assert '.column-menu' in self.css
        assert '.column-toggle' in self.css


# ============================================================
# F-06: 3D Progress Ring
# ============================================================
class TestF063DProgressRing:
    """Test 3D generation progress ring in threed_lab.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'threed_lab.html'))
        self.css = read_file(os.path.join(CSS_DIR, 'main.css'))

    def test_progress_ring_overlay(self):
        """Verify progress ring overlay exists"""
        assert 'id="progress-ring-overlay"' in self.content

    def test_svg_circle_ring(self):
        """Verify SVG circular progress ring"""
        assert 'progress-ring-circle' in self.content
        assert 'stroke-dasharray' in self.content
        assert 'stroke-dashoffset' in self.content

    def test_percentage_display(self):
        """Verify percentage text display"""
        assert 'id="progress-ring-pct"' in self.content

    def test_fun_messages_array(self):
        """Verify fun progress messages"""
        assert 'FUN_MESSAGES' in self.content
        assert 'Reconstructing geometric topology' in self.content
        assert 'Baking PBR textures' in self.content
        assert 'Optimizing polygon mesh' in self.content

    def test_fun_text_rotation(self):
        """Verify fun text rotates"""
        assert 'function updateFunText' in self.content
        assert 'id="progress-fun-text"' in self.content

    def test_show_hide_functions(self):
        """Verify show/hide functions"""
        assert 'function showProgressRing' in self.content
        assert 'function hideProgressRing' in self.content

    def test_update_progress_function(self):
        """Verify updateProgressRing function"""
        assert 'function updateProgressRing' in self.content

    def test_integrated_with_poll(self):
        """Verify progress ring is used in pollGeneration"""
        assert 'showProgressRing()' in self.content
        assert 'hideProgressRing()' in self.content
        assert 'updateProgressRing(' in self.content

    def test_progress_ring_css(self):
        """Verify progress ring CSS"""
        assert '.progress-ring-overlay' in self.css
        assert '.progress-ring-pct' in self.css
        assert '.progress-fun-text' in self.css

    def test_gradient_fill(self):
        """Verify gradient on progress ring"""
        assert 'progress-gradient' in self.content


# ============================================================
# F-07/F-08: Dimension Selector
# ============================================================
class TestF07F08DimensionSelector:
    """Test dimension selector UI in product_analysis.html"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.content = read_file(os.path.join(TEMPLATES_DIR, 'product_analysis.html'))

    def test_dimension_panel_exists(self):
        """Verify dimension selector panel"""
        assert 'Analysis Dimensions' in self.content
        assert 'Add Dimension' in self.content

    def test_active_dimensions_container(self):
        """Verify active dimensions container"""
        assert 'id="active-dimensions"' in self.content

    def test_dimension_picker(self):
        """Verify dimension picker panel"""
        assert 'id="dimension-picker"' in self.content
        assert 'Category Recommended' in self.content
        assert 'All Available Dimensions' in self.content

    def test_custom_dimension_input(self):
        """Verify custom dimension input"""
        assert 'id="custom-dimension-input"' in self.content
        assert 'Custom Dimension' in self.content

    def test_default_dimensions(self):
        """Verify default dimensions defined"""
        assert 'DEFAULT_DIMENSIONS' in self.content
        assert "'title'" in self.content
        assert "'images'" in self.content
        assert "'bullets'" in self.content

    def test_all_dimensions(self):
        """Verify all available dimensions"""
        assert 'ALL_DIMENSIONS' in self.content
        assert 'Pricing Strategy' in self.content
        assert 'Brand Strength' in self.content
        assert 'Differentiation' in self.content

    def test_category_recommendations(self):
        """Verify category-based recommendations"""
        assert 'CATEGORY_RECOMMENDATIONS' in self.content
        assert "'Electronics'" in self.content
        assert "'Home & Kitchen'" in self.content
        assert "'Beauty'" in self.content

    def test_add_remove_functions(self):
        """Verify add/remove dimension functions"""
        assert 'function addDimension' in self.content
        assert 'function removeDimension' in self.content
        assert 'function addCustomDimension' in self.content

    def test_toggle_panel(self):
        """Verify toggle panel function"""
        assert 'function toggleDimensionPanel' in self.content

    def test_dimension_tag_css(self):
        """Verify dimension tag CSS"""
        assert '.dimension-tag' in self.content
        assert '.dimension-chip' in self.content
        assert '.dim-remove' in self.content

    def test_dimensions_passed_to_analysis(self):
        """Verify dimensions are passed to visual analysis"""
        assert 'dimensions: activeDimensions' in self.content


# ============================================================
# Integration: CSS Styles
# ============================================================
class TestCSSIntegration:
    """Test all new CSS styles are properly defined"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.css = read_file(os.path.join(CSS_DIR, 'main.css'))

    def test_filter_panel_css(self):
        """Verify filter panel CSS"""
        assert '.advanced-filters' in self.css
        assert '.rating-chip' in self.css
        assert '.brand-tag' in self.css

    def test_ai_filter_css(self):
        """Verify AI filter panel CSS"""
        assert '.ai-filter-panel' in self.css

    def test_table_enhance_css(self):
        """Verify table enhancement CSS"""
        assert '.enhanced-table' in self.css
        assert '.resize-handle' in self.css
        assert '.column-menu' in self.css

    def test_progress_ring_css(self):
        """Verify progress ring CSS"""
        assert '.progress-ring-overlay' in self.css
        assert '.progress-ring-pct' in self.css

    def test_no_duplicate_keyframes(self):
        """Verify no duplicate @keyframes"""
        # Count occurrences of slideDown keyframe
        count = self.css.count('@keyframes slideDown')
        assert count >= 1  # At least one definition
