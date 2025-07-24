from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Display about page"""
    return templates.TemplateResponse("about.html", {"request": request})

@router.get("/articles", response_class=HTMLResponse)
async def articles_page(request: Request):
    """Redirect to articles router"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/articles/", status_code=302)
