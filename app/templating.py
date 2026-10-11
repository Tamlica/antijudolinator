from datetime import date

from fastapi.templating import Jinja2Templates

from app.overlay_template import format_rupiah

# One shared instance so filters/globals are registered once for every route.
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["rupiah"] = format_rupiah
templates.env.globals["today"] = date.today
