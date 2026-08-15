from app.overlay_template import DEFAULT_TEMPLATE, render_overlay_html


def test_substitutes_placeholders():
    result = render_overlay_html(
        "<b>{{supporter}}</b> gave {{amount}}: {{message}}",
        supporter="Budi",
        amount=50000,
        message="Semangat terus!",
    )
    assert result == "<b>Budi</b> gave Rp50000: Semangat terus!"


def test_escapes_donor_supplied_html_in_supporter_and_message():
    result = render_overlay_html(
        "{{supporter}} says {{message}}",
        supporter="<img src=x onerror=alert(1)>",
        amount=0,
        message="<script>alert(2)</script>",
    )
    assert "<img" not in result
    assert "<script>" not in result
    assert "&lt;img src=x onerror=alert(1)&gt;" in result
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in result


def test_supporter_defaults_to_anonymous_when_blank():
    result = render_overlay_html("{{supporter}}", supporter="", amount=0, message="")
    assert result == "Anonymous"


def test_amount_placeholder_empty_when_zero():
    result = render_overlay_html("[{{amount}}]", supporter="X", amount=0, message="")
    assert result == "[]"


def test_default_template_renders_with_expected_classes():
    result = render_overlay_html(DEFAULT_TEMPLATE, supporter="Budi", amount=1000, message="hi")
    assert 'class="supporter"' in result
    assert "Budi" in result
    assert "Rp1000" in result
    assert "hi" in result
