<?php
// ============================================================
//  api/ventas.php
//  GET  → historial de ventas (con v_ventas)
//  POST → registrar venta desde la app
// ============================================================
header('Content-Type: application/json; charset=utf-8');
require_once '../includes/db.php';

$conn   = conectar();
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    // Usar la vista que ya une clientes y usuarios
    $res  = $conn->query("SELECT * FROM v_ventas ORDER BY fecha DESC LIMIT 100");
    $rows = [];
    while ($r = $res->fetch_assoc()) $rows[] = $r;
    echo json_encode($rows);

} elseif ($method === 'POST') {
    // Cuerpo esperado:
    // { "cliente_id": 1|null, "usuario_id": 1, "items": [{"producto_id":3,"cantidad":2}, ...] }
    $data       = json_decode(file_get_contents('php://input'), true);
    $cliente_id = $data['cliente_id'] ?? null;
    $usuario_id = (int)($data['usuario_id'] ?? 1);
    $items      = $data['items'] ?? [];

    if (empty($items)) {
        http_response_code(400);
        echo json_encode(['error' => 'No hay items en la venta']);
        exit;
    }

    // Calcular total
    $total = 0;
    $lineas = [];
    foreach ($items as $item) {
        $prod_id  = (int)$item['producto_id'];
        $cantidad = (int)$item['cantidad'];
        $res = $conn->query("SELECT precio_unitario FROM productos WHERE id = $prod_id LIMIT 1");
        if ($res->num_rows === 0) continue;
        $precio   = (float)$res->fetch_assoc()['precio_unitario'];
        $subtotal = $precio * $cantidad;
        $total   += $subtotal;
        $lineas[] = ['prod_id' => $prod_id, 'cantidad' => $cantidad, 'precio' => $precio, 'subtotal' => $subtotal];
    }

    // Insertar cabecera
    $stmt = $conn->prepare("INSERT INTO ventas (cliente_id, usuario_id, fuente, total) VALUES (?,?,'app',?)");
    $stmt->bind_param('iid', $cliente_id, $usuario_id, $total);
    $stmt->execute();
    $venta_id = $conn->insert_id;
    $stmt->close();

    // Insertar detalle
    foreach ($lineas as $l) {
        $stmt = $conn->prepare("INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (?,?,?,?,?)");
        $stmt->bind_param('iiidd', $venta_id, $l['prod_id'], $l['cantidad'], $l['precio'], $l['subtotal']);
        $stmt->execute();
        $stmt->close();
    }

    echo json_encode(['ok' => true, 'venta_id' => $venta_id, 'total' => $total]);

} elseif ($method === 'DELETE') {
    // DELETE ?id=5
    $id = (int)($_GET['id'] ?? 0);
    if (!$id) { http_response_code(400); echo json_encode(['error' => 'Falta id']); exit; }
    $conn->query("DELETE FROM ventas WHERE id = $id");
    echo json_encode(['ok' => true]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Método no permitido']);
}

$conn->close();