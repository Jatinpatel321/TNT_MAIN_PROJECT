from pydantic import BaseModel, ConfigDict


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    menu_item_id: int
    quantity: int
    price_at_time: int

    model_config = ConfigDict(from_attributes=True)


class OrderItemDetailResponse(BaseModel):
    name: str
    image_url: str
    quantity: int
    price_at_time: int
    line_total: int
