# Mirrors the image used in local development: stock Odoo plus the two pip
# packages some OCA modules import at load time.
ARG ODOO_VERSION=18.0
FROM odoo:${ODOO_VERSION}

USER root
RUN pip3 install --break-system-packages --no-cache-dir \
        openupgradelib \
        odoo-test-helper
USER odoo
