from sqlalchemy.orm import Session
from app.schemas.scan import InitiateScanRequest,ScanStatus
#from app.repositories.scan_repo import ScanRepository
#from app.queue.producer import trigger_osint_scan_task

class ScanService:
    @staticmethod
    async def start_scan(db: Session, scan_date: InitaiteScanRequest):
        #Create new record in db
        #scan record, to check matching
        #Then fire off the worker queue
        #Return the data needed for the API response
        #return scan record
        pass