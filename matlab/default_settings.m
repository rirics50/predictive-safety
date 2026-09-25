function s = default_settings()
%DEFAULT_SETTINGS  Tunable settings for the polling wrapper, all in one place.
%   Anything here can be overridden by assigning the field before calling
%   run_safety_loop / poll_cycle.
%
%   EVERYTHING MARKED PLACEHOLDER NEEDS CONFIRMATION (Noel + Riya).

    s.locations = {'feed_pipeline', 'column_bottom', 'column_top', ...
                   'bottoms_output', 'distillate_output'};

    % Safety limits per location, written in the scene's own units (PSI, deg F,
    % gpm) and converted by adapt_reading itself below, so the conversion
    % factors live in exactly one place.
    % PLACEHOLDER: set just under each location's top-of-spike value in the Lua
    % scene (baseline + range) so a full demo_spike trips them. Odoo has
    % design_pressure / design_temperature per equipment but no flow limit, so
    % these are NOT the real design limits.
    %          location            P_psi  T_F   flow_gpm
    rows = {'feed_pipeline',        37,   104,   2.7; ...
            'column_bottom',        62,   190,   3.1; ...
            'column_top',           51,   153,   2.9; ...
            'bottoms_output',       61,   185,   3.1; ...
            'distillate_output',    53,   158,   2.9};
    for k = 1:size(rows, 1)
        loc = rows{k, 1};
        as_raw = struct('location', loc, 'pressure_psi', rows{k, 2}, ...
                        'temperature_F', rows{k, 3}, 'flow_gpm', rows{k, 4});
        lim = adapt_reading(as_raw, 0);   % poll time irrelevant here
        s.limits.(loc) = struct('pressure_bar', lim.pressure, ...
                                'temperature_c', lim.temperature, ...
                                'flow_kg_s', lim.flow_rate);   % dynamic field name via (...)
        % ASSUMPTION: the Odoo equipment name equals the location name. Today
        % only 'P-101' exists in Odoo; confirm the names with Riya's rewrite.
        s.equipment_names.(loc) = loc;
    end

    % PLACEHOLDER pipe geometry for check_flow (SI). Odoo has diameter in
    % inches but no length; fluid density/viscosity come from adapt_reading.
    s.pipe_geometry = struct('pipe_diameter', 0.05, 'pipe_length', 10);

    s.opts = struct();          % forwarded to the check_* functions (safety_defaults keys)

    s.poll_interval_s = 1;      % seconds between cycles
    s.max_iterations  = Inf;    % tests use small numbers; Inf = run until Ctrl-C
    s.verbose         = true;   % print one line per location per cycle

    % HTTP is OFF by default: the loop only logs what it WOULD post. Set true
    % once Riya's endpoints are live.
    s.send_http      = false;
    s.http_timeout_s = 5;

    % A Lua/Odoo fetch failure should not instantly latch the plant shut (Odoo
    % holds CRITICAL until a manual reset), so a location is skipped until this
    % many CONSECUTIVE fetch failures, then treated as bad data (CRITICAL).
    % PLACEHOLDER value.
    s.max_fetch_failures = 3;

    % Injection points (function handles; [] = use the default behaviour).
    s.fetch_fn = [];   % raw = fetch_fn(location) -> struct for adapt_reading. REQUIRED:
                       % no live temperature/flow source exists yet (Riya's rewrite).
    s.send_fn  = [];   % [ok, msg] = send_fn(url, payload); overrides send_http
    s.now_fn   = [];   % epoch seconds; default is the real clock
end
