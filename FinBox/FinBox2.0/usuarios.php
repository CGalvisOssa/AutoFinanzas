<?php
// ============================================================
//  api/usuarios.php
//  GET  → lista usuarios
//  POST → crear usuario
// ============================================================
header('Content-Type: application/json; charset=utf-8');
require_once '../includes/db.php';

$conn   = conectar();
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $res  = $conn->query("SELECT id, nombre, usuario, rol, activo FROM usuarios ORDER BY id");
    $rows = [];
    while ($r = $res->fetch_assoc()) $rows[] = $r;
    echo json_encode($rows);

} elseif ($method === 'POST') {
    $data      = json_decode(file_get_contents('php://input'), true);
    $nombre    = $conn->real_escape_string($data['nombre']    ?? '');
    $usuario   = $conn->real_escape_string($data['usuario']   ?? '');
    $contrasena= hash('sha256', $data['contrasena'] ?? '');
    $rol       = in_array($data['rol'] ?? '', ['administrador','vendedor']) ? $data['rol'] : 'vendedor';

    if (!$nombre || !$usuario) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan campos']);
        exit;
    }

    $stmt = $conn->prepare("INSERT INTO usuarios (nombre, usuario, contrasena, rol) VALUES (?,?,?,?)");
    $stmt->bind_param('ssss', $nombre, $usuario, $contrasena, $rol);
    $ok = $stmt->execute();
    $stmt->close();

    echo json_encode(['ok' => $ok, 'id' => $conn->insert_id]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Método no permitido']);
}

$conn->close();