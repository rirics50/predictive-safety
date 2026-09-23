-- Child script on /Outflow_Pipe in reactor_simulation.ttt.
-- Reference copy only: CoppeliaSim runs the copy embedded in the scene, so
-- paste changes into the scene's script editor to apply them.

sim = require('sim')

function sysCall_init()
    valveJoint = sim.getObject('/Outflow_Pipe/Emergency_Valve')
    basePressure = 45.0
    isShutDown = false
    currentPressure = basePressure

    -- Controls how often a new pressure reading is generated
    updateInterval = 20  -- seconds
    lastUpdateTime = 0

    math.randomseed(os.time())
end

function sysCall_actuation()
    -- Wall-clock seconds: the simulation isn't in real-time mode, so
    -- sim.getSimulationTime() runs ~100x faster than real time
    local t = sim.getSystemTime()
    local shutdownSignal = sim.getFloatSignal('valve_shutdown')

    if shutdownSignal and shutdownSignal > 0.5 then
        isShutDown = true
    else
        isShutDown = false
    end

    if isShutDown then
        -- Emergency state: hold the valve fully closed, and hold pressure
        -- steady. No automatic recovery - stays this way until an
        -- engineer clicks Manual Reset in Odoo.
        sim.setJointPosition(valveJoint, 1.57)
    else
        sim.setJointPosition(valveJoint, 0.0)

        -- Only generate a NEW pressure reading every `updateInterval`
        -- seconds, instead of continuously oscillating
        if t - lastUpdateTime >= updateInterval then
            lastUpdateTime = t
            -- Random reading: baseline +/- up to 12 PSI, occasionally
            -- crossing the 53 PSI threshold
            currentPressure = basePressure + (math.random() * 24 - 12)
        end
    end

    sim.setFloatSignal('live_pressure', currentPressure)
end
