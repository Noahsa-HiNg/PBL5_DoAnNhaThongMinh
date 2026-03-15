from models.schemas import EspNodeBase, EspNodeResponse
from repositories.EspNodeBase_repo import EspNodeRepo

class EspNodeController:
    def __init__(self):
        self.repo = EspNodeRepo()
    def add_new_esp_node(self, esp_node_data: EspNodeBase):
        result = self.repo.create_esp_node(esp_node_data)
        if result.get("error"):
            return {"error": "Địa chỉ MAC này đã tồn tại!"}
        return result
    def get_all_esp_nodes(self):
        return self.repo.get_all_esp_nodes()
    def delete_esp_node(self, esp_node_id: int):
        return self.repo.delete_esp_node(esp_node_id)
    def update_esp_node(self, esp_node_id: int, esp_node: EspNodeBase):
        return self.repo.update_esp_node(esp_node_id, esp_node)