#I'm not going to include database logic or the workers yet, for now it'll only receive the validated scan request

from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session
from app.schemas.scan import InitiateScanRequest, InitiateScanResponse
import uuid

router= APIRouter(prefix="/scans",tags=["Scans"])

@router.post(
    "/",
    response_model=InitiateScanResponse,
    status_code=status.HTTP_202_ACCEPTED

)

async def initiate_ctem_scan(
    request: InitiateScanRequest,
    #db stuff 

):

#Phase 1 this is the no auth scan also just a rough implementation for now until we have the other logic figured out

try:
    #I'm going to pass the validated request to the service layer
    #db stuff
    #placeholder return

    return InitiateScanResponse(
        scan_id=uuid4(),
        status="pending"

    )
except Exception as e:
    #Once proper logic is setup I'll rather log this and return a 500/specific 400 code 
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to initiate scan"
        
    )