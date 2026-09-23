sim = require('sim')

function sysCall_init()
    valveJoint = sim.getObject('/Outflow_Pipe/Emergency_Valve')
    basePressure = 45.0 -- Safe baseline pressure
    isShutDown = false
end

function sysCall_actuation()
    local t = sim.getSimulationTime()

    -- Read the shutdown signal coming from ROS 2
    local shutdownSignal = sim.getFloatSignal('valve_shutdown')

    -- Evaluate shutdown condition
    if shutdownSignal and shutdownSignal > 0.5 then
        isShutDown = true
    else
        isShutDown = false
    end

    if isShutDown then
        -- Keep the valve shut permanently when triggered
        sim.setJointPosition(valveJoint, 1.57)
    else
        -- Oscillation now peaks at 55 PSI (was capped at 49) so it can
        -- actually cross the 53 PSI threshold and trigger auto-shutdown
        local currentPressure = basePressure + (math.sin(t * 2) * 10)
        sim.setFloatSignal('live_pressure', currentPressure)
        sim.setJointPosition(valveJoint, 0.0)
    end
end
