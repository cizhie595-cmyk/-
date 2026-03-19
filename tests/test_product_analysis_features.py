"""
Tests for product_analysis.html PA-01 to PA-06 features.
Validates that all 6 new features are correctly integrated into the template.
"""
import os
import re
import pytest

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'frontend', 'templates', 'product_analysis.html'
)
CSS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'frontend', 'static', 'css', 'main.css'
)


@pytest.fixture(scope="module")
def template():
    with open(TEMPLATE_PATH, 'r') as f:
        return f.read()


# ============================================================
# PA-01: Variant Sales Donut Chart
# ============================================================
class TestPA01VariantDonut:
    def test_canvas_element_exists(self, template):
        assert 'id="chart-variant-donut"' in template

    def test_variant_legend_exists(self, template):
        assert 'id="variant-legend"' in template

    def test_render_function_exists(self, template):
        assert 'function renderVariantDonut(data)' in template

    def test_chart_type_doughnut(self, template):
        # Verify the variant chart uses doughnut type
        idx = template.find('function renderVariantDonut')
        after = template[idx:idx+2000]
        assert "type: 'doughnut'" in after

    def test_variant_legend_items_css(self, template):
        assert 'variant-legend-item' in template

    def test_called_in_review_results(self, template):
        # renderVariantDonut should be called when review analysis completes
        assert 'renderVariantDonut(data.result)' in template


# ============================================================
# PA-02: Product Lifecycle Card
# ============================================================
class TestPA02Lifecycle:
    def test_lifecycle_launch_element(self, template):
        assert 'id="lifecycle-launch"' in template

    def test_lifecycle_age_element(self, template):
        assert 'id="lifecycle-age"' in template

    def test_lifecycle_stage_element(self, template):
        assert 'id="lifecycle-stage"' in template

    def test_lifecycle_velocity_element(self, template):
        assert 'id="lifecycle-velocity"' in template

    def test_render_lifecycle_function(self, template):
        assert 'function renderLifecycle(data)' in template

    def test_lifecycle_stages_defined(self, template):
        # Should have Launch, Growth, Maturity, Decline stages
        idx = template.find('function renderLifecycle')
        after = template[idx:idx+1500]
        assert 'Launch' in after
        assert 'Growth' in after
        assert 'Maturity' in after
        assert 'Decline' in after

    def test_lifecycle_called_on_load(self, template):
        # Should be called when product data loads
        assert 'renderLifecycle(p)' in template or 'renderLifecycle(data.result)' in template


# ============================================================
# PA-03: Find Suppliers Button + Results Panel
# ============================================================
class TestPA03FindSuppliers:
    def test_find_suppliers_button(self, template):
        assert 'onclick="findSuppliers()"' in template

    def test_find_suppliers_function(self, template):
        assert 'async function findSuppliers()' in template

    def test_supplier_results_container(self, template):
        assert 'id="supplier-results"' in template

    def test_suppliers_tab(self, template):
        assert "switchAnalysisTab('suppliers')" in template

    def test_suppliers_tab_content(self, template):
        assert 'id="tab-suppliers"' in template

    def test_render_supplier_results_function(self, template):
        assert 'function renderSupplierResults(suppliers)' in template

    def test_supplier_card_css(self, template):
        assert 'supplier-card' in template

    def test_image_search_api_call(self, template):
        assert '/v1/supply/image-search' in template

    def test_supplier_meta_fields(self, template):
        # Should show price, MOQ, supplier name, location, sales, score
        idx = template.find('renderSupplierResults')
        after = template[idx:idx+2000]
        assert 'Price' in after
        assert 'MOQ' in after
        assert 'Supplier' in after


# ============================================================
# PA-04: Generate 3D Model Button
# ============================================================
class TestPA04Generate3D:
    def test_generate_3d_button(self, template):
        assert 'onclick="generate3DModel()"' in template

    def test_generate_3d_function(self, template):
        assert 'function generate3DModel()' in template

    def test_navigates_to_3d_lab(self, template):
        idx = template.find('function generate3DModel')
        after = template[idx:idx+800]
        assert '/3d-lab' in after

    def test_passes_image_url(self, template):
        idx = template.find('function generate3DModel')
        after = template[idx:idx+500]
        assert 'image_url' in after

    def test_button_text(self, template):
        assert 'Generate 3D' in template


# ============================================================
# PA-05: Visual Analysis Complete Results
# ============================================================
class TestPA05VisualAnalysis:
    def test_marketing_structure_container(self, template):
        assert 'id="marketing-structure"' in template

    def test_text_semantic_container(self, template):
        assert 'id="text-semantic"' in template

    def test_color_psychology_container(self, template):
        assert 'id="color-psychology"' in template

    def test_font_hierarchy_container(self, template):
        assert 'id="font-hierarchy"' in template

    def test_brand_positioning_container(self, template):
        assert 'id="brand-positioning"' in template

    def test_render_marketing_structure(self, template):
        assert 'function renderMarketingStructure(data)' in template

    def test_render_text_semantic(self, template):
        assert 'function renderTextSemantic(data)' in template

    def test_render_color_psychology(self, template):
        assert 'function renderColorPsychology(data)' in template

    def test_render_font_hierarchy(self, template):
        assert 'function renderFontHierarchy(data)' in template

    def test_render_brand_positioning(self, template):
        assert 'function renderBrandPositioning(data)' in template

    def test_called_in_visual_results(self, template):
        # All PA-05 renderers should be called when visual analysis completes
        assert 'renderMarketingStructure(data.result)' in template
        assert 'renderTextSemantic(data.result)' in template
        assert 'renderColorPsychology(data.result)' in template
        assert 'renderFontHierarchy(data.result)' in template
        assert 'renderBrandPositioning(data.result)' in template

    def test_usp_tag_css(self, template):
        assert 'usp-tag' in template

    def test_color_swatch_css(self, template):
        assert 'color-swatch' in template


# ============================================================
# PA-06: Fake Review Filter Stats
# ============================================================
class TestPA06ReviewFilter:
    def test_review_filter_stats_container(self, template):
        assert 'id="review-filter-stats"' in template

    def test_render_function(self, template):
        assert 'function renderReviewFilterStats(data)' in template

    def test_fake_rate_display(self, template):
        idx = template.find('function renderReviewFilterStats')
        after = template[idx:idx+2000]
        assert 'Suspected Fake Rate' in after

    def test_authentic_vs_filtered(self, template):
        idx = template.find('function renderReviewFilterStats')
        after = template[idx:idx+2000]
        assert 'Authentic' in after
        assert 'Filtered' in after

    def test_filter_reasons_display(self, template):
        idx = template.find('function renderReviewFilterStats')
        after = template[idx:idx+2000]
        assert 'Filter Reasons' in after

    def test_called_in_review_results(self, template):
        assert 'renderReviewFilterStats(data.result)' in template

    def test_filter_bar_css(self, template):
        assert 'filter-bar' in template


# ============================================================
# Integration Tests
# ============================================================
class TestIntegration:
    def test_all_tabs_present(self, template):
        tabs = ['visual', 'reviews', 'bsr', 'competitors', 'suppliers']
        for tab in tabs:
            assert f"switchAnalysisTab('{tab}')" in template

    def test_all_tab_contents_present(self, template):
        tab_ids = ['tab-visual', 'tab-reviews', 'tab-bsr', 'tab-competitors', 'tab-suppliers']
        for tid in tab_ids:
            assert f'id="{tid}"' in template

    def test_switch_tab_includes_suppliers(self, template):
        idx = template.find('function switchAnalysisTab')
        after = template[idx:idx+600]
        assert "'suppliers'" in after

    def test_action_bar_has_all_buttons(self, template):
        assert 'Visual Analysis' in template
        assert 'Review Analysis' in template
        assert 'Download Assets' in template
        assert 'Find Suppliers' in template
        assert 'Generate 3D' in template
        assert 'View on Amazon' in template

    def test_template_is_valid_html(self, template):
        # Basic check: all opened divs are closed
        open_divs = template.count('<div')
        close_divs = template.count('</div>')
        # Allow small difference due to Jinja2 blocks
        assert abs(open_divs - close_divs) <= 2

    def test_no_syntax_errors_in_js(self, template):
        # Check for common JS syntax issues
        assert template.count('function ') > 15  # Should have many functions
        # No unclosed template literals
        backtick_count = template.count('`')
        assert backtick_count % 2 == 0, "Unclosed template literal"

    def test_total_line_count(self, template):
        lines = template.count('\n') + 1
        assert lines > 1200, f"Expected >1200 lines, got {lines}"
