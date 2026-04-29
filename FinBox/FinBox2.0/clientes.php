<?php
// ============================================================
//  api/clientes.php
//  GET  → lista clientes
//  POST → agrega cliente
// ============================================================
header('Content-Type: application/json; charset=utf-8');
require_once '../includes/db.php';

$conn   = conectar();
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $res  = $conn->query("SELECT * FROM clientes ORDER BY nombre");
    $rows = [];
    while ($r = $res->fetch_assoc()) $rows[] = $r;
    echo json_encode($rows);

} elseif ($method === 'POST') {
    $data     = json_decode(file_get_contents('php://input'), true);
    $cedula   = $conn->real_escape_string($data['cedula']    ?? '');
    $nombre   = $conn->real_escape_string($data['nombre']    ?? '');
    $telefono = $conn->real_escape_string($data['telefono']  ?? '');
    $direccion= $conn->real_escape_string($data['direccion'] ?? '');

    if (!$cedula || !$nombre) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan campos obligatorios']);
        exit;
    }

    $stmt = $conn->prepare("INSERT INTO clientes (cedula, nombre, telefono, direccion) VALUES (?,?,?,?)");
    $stmt->bind_param('ssss', $cedula, $nombre, $telefono, $direccion);
    $ok = $stmt->execute();
    $stmt->close();

    echo json_encode(['ok' => $ok, 'id' => $conn->insert_id]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Método no permitido']);
}

$conn->close();