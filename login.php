<?php
session_start();
require_once 'config.php';

$erreur = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $email = $_POST['email'];
    $password = $_POST['password'];

    $sql = "SELECT * FROM utilisateurs WHERE email = ?";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $email);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($user = $result->fetch_assoc()) {
        if ($password === $user['mot_de_passe']) {
            $_SESSION['user_id'] = $user['id'];
            $_SESSION['nom'] = $user['nom'];
            $_SESSION['role'] = $user['role'];
            
            header("Location: dashboard.php");
            exit();
        } else {
            $erreur = "Mot de passe incorrect.";
        }
    } else {
        $erreur = "Utilisateur non trouvé.";
    }
}
?>

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Connexion - Gestion Pharmacie</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h2 { text-align: center; color: #2c3e50; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #333; }
        input[type="email"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background-color: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #219150; }
        .error { color: red; margin-bottom: 15px; text-align: center; }
    </style>
</head>
<body>

<div class="login-card">
    <h2>Connexion Pharmacie</h2>
    
    <?php if (!empty($erreur)): ?>
        <p class="error"><?php echo $erreur; ?></p>
    <?php endif; ?>

    <form action="login.php" method="POST">
        <div class="form-group">
            <label>Adresse Email :</label>
            <input type="email" name="email" required placeholder="admin@pharmacie.com">
        </div>
        <div class="form-group">
            <label>Mot de passe :</label>
            <input type="password" name="password" required placeholder="••••••••">
        </div>
        <button type="submit">Se connecter</button>
    </form>
</div>

</body>
</html>