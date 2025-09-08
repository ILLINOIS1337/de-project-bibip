from models import Car, CarFullInfo, CarStatus, Model, ModelSaleStats, Sale
import os.path as op
import json
from collections import defaultdict
from datetime import datetime
from typing import DefaultDict


class CarService:
    def __init__(self, root_directory_path: str) -> None:
        self.rdir_path = root_directory_path

    # Метод чтения файла.
    def _load_json_file(self, filename: str):
        path = op.join(self.rdir_path, filename)
        if not op.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            return json.loads(content) if content else []

    # Метод записи файла.
    def _save_json_file(self, filename: str, data) -> None:
        path = op.join(self.rdir_path, filename)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    # Задание 1. Сохранение моделей
    def add_model(self, model: Model) -> Model:
        model_index = self._load_json_file("models_index.txt")
        model_index.append({"id": model.id, "row_number": len(model_index)})
        model_index.sort(key=lambda x: x["id"])
        self._save_json_file("models_index.txt", model_index)

        models_data = self._load_json_file("models.txt")
        models_data.append(json.loads(model.model_dump_json()))
        self._save_json_file("models.txt", models_data)
        return model

    # # Задание 1.1 Сохранение автомобилей
    def add_car(self, car: Car) -> Car:
        car_index = self._load_json_file("cars_index.txt")
        car_index.append({"vin": car.vin, "row_number": len(car_index)})
        self._save_json_file("cars_index.txt", car_index)

        cars_data = self._load_json_file("cars.txt")
        car_dict = json.loads(car.model_dump_json())
        car_dict["status"] = car.status.value
        cars_data.append(car_dict)
        self._save_json_file("cars.txt", cars_data)
        return car

    # # Задание 2. Сохранение продаж.
    def sell_car(self, sale: Sale) -> Car:
        sale_index = self._load_json_file("sales_index.txt")
        sale_index.append({"sales_number": sale.sales_number,
                           "row_number": len(sale_index)})
        self._save_json_file("sales_index.txt", sale_index)

        sales_data = self._load_json_file("sales.txt")
        sales_data.append(json.loads(sale.model_dump_json()))
        self._save_json_file("sales.txt", sales_data)

        car_index = self._load_json_file("cars_index.txt")
        car_data = self._load_json_file("cars.txt")
        target = next((i for i in car_index if i["vin"] == sale.car_vin), None)
        if target is None:
            raise ValueError("Car VIN not found")

        car = car_data[target["row_number"]]
        car["status"] = CarStatus.sold.value
        car_data[target["row_number"]] = car
        self._save_json_file("cars.txt", car_data)
        return Car.model_validate(car)

    # # Задание 3. Доступные к продаже
    def get_cars(self, status: CarStatus) -> list[Car]:
        cars = self._load_json_file("cars.txt")
        filtered = [Car.model_validate(c)
                    for c in cars if c.get("status") == status.value]
        return filtered

    # # Задание 4. Детальная информация
    def get_car_info(self, vin: str) -> CarFullInfo | None:
        car_index = self._load_json_file("cars_index.txt")
        cars_data = self._load_json_file("cars.txt")
        models_index = self._load_json_file("models_index.txt")
        models_data = self._load_json_file("models.txt")
        sales_data = self._load_json_file("sales.txt")

        car_entry = next((i for i in car_index if i["vin"] == vin), None)
        if car_entry is None:
            return None
        car = cars_data[car_entry["row_number"]]

        model_entry = next(
            (m for m in models_index if m["id"] == car["model"]), None)
        if model_entry is None:
            return None
        model = models_data[model_entry["row_number"]]

        sales_entry = next((s for s in sales_data if s["car_vin"] == vin
                            and not s.get("is_deleted")), None)

        car_date_start = (
            datetime.fromisoformat(car["date_start"])
            if isinstance(car["date_start"], str)
            else car["date_start"]
        )

        return CarFullInfo(
            vin=vin,
            car_model_name=model["name"],
            car_model_brand=model["brand"],
            price=car["price"],
            date_start=car_date_start,
            status=car["status"],
            sales_date=sales_entry["sales_date"] if sales_entry else None,
            sales_cost=sales_entry["cost"] if sales_entry else None,
        )

    # # Задание 5. Обновление ключевого поля
    def update_vin(self, vin: str, new_vin: str) -> Car:
        car_index = self._load_json_file("cars_index.txt")
        cars_data = self._load_json_file("cars.txt")

        entry = next((i for i in car_index if i["vin"] == vin), None)
        if entry is None:
            raise ValueError("VIN not found")

        cars_data[entry["row_number"]]["vin"] = new_vin

        for i in car_index:
            if i["vin"] == vin:
                i["vin"] = new_vin
                break

        # Сохранить отсортированный индекс по новому VIN
        self._save_json_file("cars_index.txt", sorted(
            car_index, key=lambda x: x["vin"]))
        self._save_json_file("cars.txt", cars_data)
        return Car.model_validate(cars_data[entry["row_number"]])

    # # Задание 6. Удаление продажи
    def revert_sale(self, sales_number: str) -> Car:
        sales_data = self._load_json_file("sales.txt")
        cars_data = self._load_json_file("cars.txt")
        car_index = self._load_json_file("cars_index.txt")

        sale_entry = next((
            s for s in sales_data if s["sales_number"] == sales_number), None)
        if sale_entry is None:
            raise ValueError("Sale not found")

        found_sale_idx = -1
        for idx, s in enumerate(sales_data):
            if s["sales_number"] == sales_number:
                s["is_deleted"] = True
                found_sale_idx = idx
                break

        if found_sale_idx == -1:
            raise ValueError("Sale not found in data")

        self._save_json_file("sales.txt", sales_data)
        car_vin = sales_data[found_sale_idx]["car_vin"]
        entry = next((i for i in car_index if i["vin"] == car_vin), None)
        if entry is None:
            raise ValueError("Car not found for this sale")

        cars_data[entry["row_number"]]["status"] = CarStatus.available.value
        self._save_json_file("cars.txt", cars_data)

        return Car.model_validate(cars_data[entry["row_number"]])

    # # Задание 7. Самые продаваемые модели
    def top_models_by_sales(self) -> list[ModelSaleStats]:
        sales_data = self._load_json_file("sales.txt")
        cars_data = self._load_json_file("cars.txt")
        models_data = self._load_json_file("models.txt")

        sales_count: DefaultDict[int, int] = defaultdict(int)

        model_info_map = {m["id"]: {"name": m["name"], "brand": m["brand"]}
                          for m in models_data}
        car_info_map = {c["vin"]: c for c in cars_data}

        for sale in sales_data:
            if sale.get("is_deleted"):
                continue
            vin = sale["car_vin"]
            car = car_info_map.get(vin)
            if not car:
                continue
            sales_count[car["model"]] += 1

        top_sales_list = []
        for model_id, count in sales_count.items():
            model_info = model_info_map.get(model_id)
            if model_info:
                top_sales_list.append((count, model_info["name"], model_id))

        top_sales_list.sort(key=lambda x: (-x[0], x[1]))

        result = []
        for count, model_name, model_id in top_sales_list[:3]:
            model_info = model_info_map.get(model_id)
            if model_info:
                result.append(ModelSaleStats(
                    car_model_name=model_info["name"],
                    brand=model_info["brand"],
                    sales_number=count
                ))
        return result
