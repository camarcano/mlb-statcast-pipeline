#!/bin/bash
set -e

INSTALL_DIR="${INSTALL_DIR:-/var/www/mlb-statcast-pipeline}"
SERVER_NAME="dashboard.datanalytics.pro"
SERVER_ALIAS="www.dashboard.datanalytics.pro"

echo "=== Apache + mod_wsgi Setup for Savant Analytics ==="

# 1. Install mod_wsgi
echo "Installing libapache2-mod-wsgi-py3..."
sudo apt install -y libapache2-mod-wsgi-py3

# 2. Enable mod_wsgi
sudo a2enmod wsgi

# 3. Create Apache vhost config
echo "Creating Apache virtual host..."
sudo tee /etc/apache2/sites-available/savant-analytics.conf > /dev/null <<EOF
<VirtualHost *:80>
    ServerName ${SERVER_NAME}
    ServerAlias ${SERVER_ALIAS}

    WSGIDaemonProcess savant user=www-data group=www-data threads=5 \\
        python-home=${INSTALL_DIR}/venv \\
        python-path=${INSTALL_DIR}
    WSGIProcessGroup savant
    WSGIScriptAlias / ${INSTALL_DIR}/webapp/wsgi.py

    <Directory ${INSTALL_DIR}/webapp>
        Require all granted
    </Directory>

    Alias /static ${INSTALL_DIR}/webapp/static
    <Directory ${INSTALL_DIR}/webapp/static>
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/savant_error.log
    CustomLog \${APACHE_LOG_DIR}/savant_access.log combined
</VirtualHost>
EOF

# 4. Enable the site, disable default
sudo a2ensite savant-analytics.conf
sudo a2dissite 000-default.conf 2>/dev/null || true

# 5. Set permissions so www-data can read the database
echo "Setting database permissions..."
chmod 644 ${INSTALL_DIR}/data/savant.db 2>/dev/null || true
chmod 644 ${INSTALL_DIR}/data/savant.db-wal 2>/dev/null || true
chmod 644 ${INSTALL_DIR}/data/savant.db-shm 2>/dev/null || true
chmod 755 ${INSTALL_DIR}/data

# 6. Test config and reload
echo "Testing Apache config..."
sudo apache2ctl configtest
sudo systemctl reload apache2

echo ""
echo "=== Apache setup complete ==="
echo "Site: http://${SERVER_NAME}"
echo "Error log: /var/log/apache2/savant_error.log"
echo ""
echo "Note: For HTTPS, install certbot and run:"
echo "  sudo certbot --apache -d ${SERVER_NAME} -d ${SERVER_ALIAS}"
