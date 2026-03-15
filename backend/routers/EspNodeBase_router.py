from fastapi import APIRouter, HTTPException
from models.schemas import EspNodeBase, EspNodeResponse
from controllers.EspNodeBase_controller import EspNodeController

router = APIRouter(prefix="/api/nodes", tags=["Quản lý ESP Node"])

controller = EspNodeController()

@router.post("/")
def create_esp_node_api(esp_node_data: EspNodeBase):
    result = controller.add_new_esp_node(esp_node_data)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result
@router.get("/")
def get_all_esp_nodes_api():
    return controller.get_all_esp_nodes()
@router.delete("/{esp_node_id}")
def delete_esp_node_api(esp_node_id: int):
    return controller.delete_esp_node(esp_node_id)
@router.put("/{esp_node_id}")
def update_esp_node_api(esp_node_id: int, esp_node: EspNodeBase):
    return controller.update_esp_node(esp_node_id, esp_node)