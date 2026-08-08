<?php
session_start();
if (!isset($_SESSION['user_id'])) {
    header("Location: login.php");
    exit();
}
?>

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Tableau de bord</title>
</head>
<body>
    <h1>Bienvenue, <?php echo $_SESSION['nom']; ?> !</h1>
    <p>Vous êtes connecté avec succès.</p>
    <a href="login.php">Se déconnecter</a>
</body>
</html>