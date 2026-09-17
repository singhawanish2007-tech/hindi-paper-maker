import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.curriculum_data import DEFAULT_BLUEPRINTS
from app.models.paper import CustomBlueprint
from app.schemas.paper import BlueprintValidationRequest, BlueprintValidationResponse
from app.services.paper_validator import validate_blueprint_data

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])

@router.get("")
def get_blueprints(grade: str = "10", db: Session = Depends(get_db)):
    """
    Returns available blueprints matching the grade, plus custom saved blueprints.
    """
    default_list = []
    for key, bp in DEFAULT_BLUEPRINTS.items():
        if grade in bp.get("grade_range", []):
            default_list.append({"id": key, "is_default": True, **bp})
            
    custom_bps = db.query(CustomBlueprint).filter(CustomBlueprint.grade == grade).all()
    custom_list = []
    for cb in custom_bps:
        try:
            struct = json.loads(cb.structure_json)
        except Exception:
            struct = {}
        custom_list.append({
            "id": f"custom_{cb.id}",
            "db_id": cb.id,
            "is_default": False,
            "title": cb.title,
            "grade": cb.grade,
            "total_marks": cb.total_marks,
            "duration": cb.duration,
            "sections": struct.get("sections", [])
        })
        
    return {
        "grade": grade,
        "default_blueprints": default_list,
        "custom_blueprints": custom_list
    }

@router.post("")
def save_custom_blueprint(
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    title = data.get("title", "कस्टम ब्लूप्रिंट")
    grade = str(data.get("grade", "10"))
    total_marks = data.get("total_marks", 40)
    duration = data.get("duration", "२ घंटे")
    sections = data.get("sections", [])
    
    val = validate_blueprint_data(total_marks, sections)
    if not val["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य ब्लूप्रिंट: {'; '.join(val['errors'])}"
        )
        
    cb = CustomBlueprint(
        title=title,
        grade=grade,
        total_marks=total_marks,
        duration=duration,
        structure_json=json.dumps({"sections": sections}, ensure_ascii=False)
    )
    db.add(cb)
    db.commit()
    db.refresh(cb)
    return {"id": cb.id, "message": "ब्लूप्रिंट सफलतापूर्वक सहेजा गया।"}

@router.post("/validate", response_model=BlueprintValidationResponse)
def validate_blueprint_route(request: BlueprintValidationRequest):
    result = validate_blueprint_data(request.total_marks, request.sections)
    return result
