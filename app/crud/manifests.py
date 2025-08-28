from typing import List
from sqlalchemy.orm import Session

from crud.base import CRUDBase
from core.enums import OrderBy
from models.models import Manifest
from schemas.manifests import ManifestCreate, ManifestUpdate

class CRUDManifest(CRUDBase[Manifest, ManifestCreate, ManifestUpdate]):
    def get_by_deployment(
        self,
        db: Session,
        *,
        deployment_id: int,
        skip: int = 0,
        limit: int = 100,
        order_by: OrderBy = OrderBy.CREATED_AT_DESC
    ) -> List[Manifest]:
        query = db.query(Manifest).filter(
            Manifest.deployment_id == deployment_id,
            Manifest.deleted_at == None
        )
        query = self._apply_ordering(query, Manifest, order_by)
        return query.offset(skip).limit(limit).all()


crud_manifest = CRUDManifest(Manifest)