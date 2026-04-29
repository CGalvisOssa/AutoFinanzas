<?php
// ============================================================
//  api/productos.php
//  GET  → lista todos los productos
//  POST → agrega un producto nuevo
// ============================================================
header('Content-Type: application/json; charset=utf-8');
require_once '../includes/db.php';

$conn   = conectar();
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $res  = $conn->query("SELECT * FROM productos WHERE activo = 1 ORDER BY id");
    $rows = [];
    while ($r = $res->fetch_assoc()) $rows[] = $r;
    echo json_encode($rows);

} elseif ($method === 'POST') {
    $data   = json_decode(file_get_contents('php://input'), true);
    $codigo = $conn->real_escape_string($data['codigo'] ?? '');
    $nombre = $conn->real_escape_string($data['nombre'] ?? '');
    $precio = (float)($data['precio_unitario'] ?? 0);

    if (!$codigo || !$nombre) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan campos obligatorios']);
        exit;
    }

    $stmt = $conn->prepare("INSERT INTO productos (codigo, nombre, precio_unitario) VALUES (?, ?, ?)");
    $stmt->bind_param('ssd', $codigo, $nombre, $precio);
    $ok = $stmt->execute();
    $stmt->close();

    echo json_encode(['ok' => $ok, 'id' => $conn->insert_id]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Método no permitido']);
}

$conn->close();