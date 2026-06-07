from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cache, product_adapter, products_adapter
from app.database import get_db, init_db
from app.models import Product
from app.schemas import DeleteProductsRequest, ProductCreate, ProductRead, TaskResponse
from app.tasks import delete_products_by_ids, import_products_from_csv

app = FastAPI(title="Homework 6: Background tasks and Redis cache")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    cache.invalidate_products()
    return product


@app.get("/products", response_model=list[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ProductRead]:
    cache_key = f"products:list:{skip}:{limit}"
    cached = cache.get_json(cache_key)
    if cached is not None:
        return products_adapter.validate_python(cached)

    products = db.scalars(select(Product).offset(skip).limit(limit)).all()
    response = [ProductRead.model_validate(product) for product in products]
    cache.set_json(cache_key, [item.model_dump(mode="json") for item in response])
    return response


@app.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead:
    cache_key = f"products:item:{product_id}"
    cached = cache.get_json(cache_key)
    if cached is not None:
        return product_adapter.validate_python(cached)

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    response = ProductRead.model_validate(product)
    cache.set_json(cache_key, response.model_dump(mode="json"))
    return response


@app.post("/tasks/import-csv", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
def schedule_csv_import(csv_path: str, background_tasks: BackgroundTasks) -> TaskResponse:
    background_tasks.add_task(import_products_from_csv, csv_path)
    return TaskResponse(status="accepted", detail="CSV import task has been scheduled")


@app.post("/tasks/delete-products", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
def schedule_product_deletion(
    payload: DeleteProductsRequest,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    background_tasks.add_task(delete_products_by_ids, payload.ids)
    return TaskResponse(status="accepted", detail="Product deletion task has been scheduled")
