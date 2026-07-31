from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.domains import (
    add_domain_for_verification,
    delete_domain,
    get_domains,
)
from app.schemas.domain import AddDomainRequest, DomainSortField, SortOrder


def _current_user():
    return{"sub": "kc-123", "email": "test@example.com"}


#Phase 2 
#test adding domain successs verified 
# POST /domains/ (add domain)happy path 
@pytest.mark.asyncio
@patch("app.api.routes.domains.DomainService.add_domain",new_callable=AsyncMock)
@patch("app.api.routes.domains.get_user_id_by_provider_id",new_callable=AsyncMock)
async def test_add_domain_for_verification_success(mock_get_user_id,mock_add_domain):
    db = AsyncMock()
    user_id = uuid4()
    mock_get_user_id.return_value = user_id
    mock_add_domain.return_value = {"domain" : "example.com"}

    request = AddDomainRequest(domain= "example.com")

    result = await add_domain_for_verification(request, db ,_current_user())

    mock_get_user_id.assert_awaited_once_with(db,"kc-123")
    mock_add_domain.assert_awaited_once_with(db ,domain="example.com",user_id =user_id)
    assert result == {"domain":"example.com"}



#Phase 2 
#test adding domain successs verified 
# POST /domains/ (add domain)Error path
#test verification return 401
@pytest.mark.asyncio
@patch("app.api.routes.domains.get_user_id_by_provider_id",new_callable= AsyncMock)
async def test_add_domain_for_verification_missing_user_raises_401(mock_get_user_id):
    db = AsyncMock()
    mock_get_user_id.return_value =  None

    request = AddDomainRequest(domain= "example.com")

    with pytest.raises(HTTPException) as exc_info:
        await add_domain_for_verification(request,db ,_current_user())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not present."

#test domain success
@pytest.mark.asyncio
@patch("app.api.routes.domains.DomainService.list_domains",new_callable= AsyncMock)
@patch("app.api.routes.domains.get_user_id_by_provider_id",new_callable= AsyncMock)
async def test_get_domains_success(mock_get_user_id,mock_list_domains):
    db = AsyncMock()
    user_id = uuid4()
    mock_get_user_id.return_value = user_id

    mock_list_domains.return_value = {"items":[],"counts":{},"pagination":{}}

    result = await get_domains(
        verification_status = None,
        search = None,
        sort = DomainSortField.CREATED_AT,
        order = SortOrder.DESC,
        limit = 20,
        offset = 0,
        db = db,
        current_user = _current_user(),
    )

    mock_list_domains.assert_awaited_once_with(
        db,
        user_id = user_id,
        verification_status = None,
        search = None,
        sort = DomainSortField.CREATED_AT,
        order = SortOrder.DESC,
        limit = 20,
        offset = 0,
    )

    assert  result == {"items":[], "counts":{}, "pagination" :{}}


#test missing user
@pytest.mark.asyncio
@patch("app.api.routes.domains.DomainService.list_domains",new_callable= AsyncMock)
@patch("app.api.routes.domains.get_user_id_by_provider_id",new_callable=AsyncMock)
async def test_get_domains_missing_user_raises_401(mock_get_user_id, mock_list_domains):
    db = AsyncMock()
    mock_get_user_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_domains(
            verification_status = None,
            search = None,
            sort = DomainSortField.CREATED_AT,
            order = SortOrder.DESC,
            limit = 20,
            offset = 0,
            db = db,
            current_user = _current_user(),
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not present."

# phase 2 
#test delete domain
##phase 2 
#DELETE /domains/{domain_id} delete domain happy path 
@pytest.mark.asyncio
@patch("app.api.routes.domains.DomainService.delete_domain",new_callable= AsyncMock)
@patch("app.api.routes.domains.get_user_id_by_provider_id",new_callable=AsyncMock)
async def test_delete_domain_success(mock_get_user_id, mock_delete_domain) :
    db = AsyncMock()
    user_id = uuid4()
    domain_id = uuid4()
    mock_get_user_id.return_value = user_id

    result = await delete_domain(domain_id,db,_current_user())

    mock_delete_domain.assert_awaited_once_with(db ,domain_id =domain_id ,user_id = user_id)
    assert result.status_code ==204

#test delete domain fail
#phase 2 
#DELETE /domains/{domain_id} delete domain error path
@pytest.mark.asyncio
@patch("app.api.routes.domains.get_user_id_by_provider_id",new_callable=AsyncMock)
async def test_delete_domain_missing_user_raises_401(mock_get_user_id) :
    db = AsyncMock()
    mock_get_user_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await delete_domain(uuid4(),db,_current_user())

    assert exc_info.value.status_code ==401
    assert exc_info.value.detail == "User not present."