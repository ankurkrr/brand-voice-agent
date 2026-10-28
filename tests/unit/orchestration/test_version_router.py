import pytest
from core.orchestration.version_router import route_agent3
from domain.models.agent3_request import Agent3Request

@pytest.mark.asyncio
async def test_version_router_directs_v1_correctly(mocker):
    # Setup - mock the underlying entry points
    v1_mock = mocker.patch("core.orchestration.version_router.run_agent3_v1")
    v2_mock = mocker.patch("core.orchestration.version_router.run_agent3_v2")
    
    request = mocker.MagicMock(spec=Agent3Request)
    
    # Execute routing for V1
    await route_agent3("v1", request)
    
    # Assert isolation
    v1_mock.assert_called_once_with(request)
    v2_mock.assert_not_called()

@pytest.mark.asyncio
async def test_version_router_directs_v2_correctly(mocker):
    v1_mock = mocker.patch("core.orchestration.version_router.run_agent3_v1")
    v2_mock = mocker.patch("core.orchestration.version_router.run_agent3_v2")
    
    request = mocker.MagicMock(spec=Agent3Request)
    
    # Execute routing for V2
    await route_agent3("v2", request)
    
    # Assert isolation
    v2_mock.assert_called_once_with(request)
    v1_mock.assert_not_called()
    
@pytest.mark.asyncio
async def test_version_router_invalid_version(mocker):
    request = mocker.MagicMock(spec=Agent3Request)
    with pytest.raises(ValueError, match="Unknown mode"):
        await route_agent3("v3", request)
