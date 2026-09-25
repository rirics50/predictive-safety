function url = odoo_url(cfg, path)
%ODOO_URL  Join cfg.odoo_base_url and an endpoint path.
%   url = odoo_url(cfg, '/api/safety_status/P-101')
%   Tolerates a missing or doubled slash, so a path typo can't produce a bad URL.

    url = [cfg.odoo_base_url '/' regexprep(path, '^/+', '')];
end
