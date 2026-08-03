<?php
$host = "localhost";
$user = "root";
$pass = "";
$db   = "pharmacie_db";

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    die("Échec de la connexion : " . $conn->connect_error);
}
?>