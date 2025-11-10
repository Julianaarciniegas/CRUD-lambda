import os
import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

# Configuración de la tabla
TABLE_NAME = os.environ.get("TABLE_NAME", "Usuarios")
REGION = os.environ.get("REGION")
dynamodb = boto3.resource("dynamodb", region_name=REGION) if REGION else boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# --- FUNCIONES AUXILIARES ---

# Convertidor de Decimal -> int o float según corresponda
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Si es un número entero (sin parte decimal), lo convertimos a int
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def response(status_code, message, data=None):
    body = {"message": message}
    if data is not None:
        body["data"] = data
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder)
    }

# --- FUNCIÓN PRINCIPAL ---
def lambda_handler(event, context):
    http_method = event.get("httpMethod")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    body = event.get("body")

    # Validar cuerpo JSON (para POST/PUT)
    if http_method in ["POST", "PUT"]:
        if not body:
            return response(400, "Error: El cuerpo de la solicitud está vacío o es inválido.")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return response(400, "Error: El cuerpo no es un JSON válido (revisa comillas y formato).")

    try:
        # --- CREATE ---
        if http_method == "POST" and path.rstrip("/").endswith("/items"):
            item = body
            if "id" not in item:
                item["id"] = str(uuid.uuid4())
            table.put_item(Item=item)
            return response(201, "Usuario creado con éxito.", data=item)

        # --- READ ALL ---
        if http_method == "GET" and path.rstrip("/").endswith("/items") and not path_params.get("id"):
            res = table.scan()
            return response(200, "Listado obtenido correctamente.", data=res.get("Items", []))

        # --- READ ONE ---
        if http_method == "GET" and path_params.get("id"):
            item_id = path_params["id"]
            res = table.get_item(Key={"id": item_id})
            if "Item" in res:
                return response(200, "Usuario encontrado.", data=res["Item"])
            return response(404, "Usuario no encontrado.")

        # --- UPDATE ---
        if http_method == "PUT" and path_params.get("id"):
            item_id = path_params["id"]
            body["id"] = item_id
            table.put_item(Item=body)
            return response(200, "Usuario actualizado correctamente.", data=body)

        # --- DELETE ---
        if http_method == "DELETE" and path_params.get("id"):
            item_id = path_params["id"]
            table.delete_item(Key={"id": item_id})
            return response(200, "Usuario eliminado correctamente.")

        return response(400, "Ruta o método no soportado.")
    
    except Exception as e:
        print("Error:", str(e))
        return response(500, "Error interno del servidor.", data={"error": str(e)})
