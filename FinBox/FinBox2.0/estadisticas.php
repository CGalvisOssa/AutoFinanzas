<?php
// ============================================================
//  api/estadisticas.php
//  GET ?tipo=top_productos|por_fuente|resumen
// ============================================================
header('Content-Type: application/json; charset=utf-8');
require_once '../includes/db.php';

$conn = conectar();
$tipo = $_GET['tipo'] ?? 'resumen';

switch ($tipo) {

    case 'top_productos':
        $res  = $conn->query("SELECT * FROM v_top_productos LIMIT 10");
        $rows = [];
        while ($r = $res->fetch_assoc()) $rows[] = $r;
        echo json_encode($rows);
        break;

    case 'por_fuente':
        $res  = $conn->query("SELECT * FROM v_ventas_por_fuente");
        $rows = [];
        while ($r = $res->fetch_assoc()) $rows[] = $r;
        echo json_encode($rows);
        break;

    case 'resumen':
    default:
        $hoy = date('Y-m-d');

        $r1 = $conn->query("SELECT COUNT(*) AS total, COALESCE(SUM(total),0) AS ingresos FROM ventas WHERE DATE(fecha) = '$hoy'")->fetch_assoc();
        $r2 = $conn->query("SELECT COUNT(*) AS total FROM ventas")->fetch_assoc();
        $r3 = $conn->query("SELECT COUNT(*) AS total FROM clientes")->fetch_assoc();

        echo json_encode([
            'ventas_hoy'      => (int)$r1['total'],
            'ingresos_hoy'    => (float)$r1['ingresos'],
            'ventas_total'    => (int)$r2['total'],
            'total_clientes'  => (int)$r3['total'],
        ]);
        break;
}

$conn->close();