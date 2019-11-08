"""

Removes non-linear ground reaction force signal drift in a stepwise manner. It is intended
for running ground reaction force data commonly analyzed in the field of Biomechanics. The aerial phase before and after
a given step are used to tare the signal instead of assuming an overall linear trend or signal offset.

Licensed under an MIT License (c) Ryan Alcantara 2019

Distributed here: https://github.com/alcantarar/dryft


"""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def detrend(force_f, aerial, aerial_loc):
    """Remove drift from running ground reaction force signal based on aerial phases.

    Parameters
    ----------
    force_f : `ndarray`
        Filtered ground reaction force signal [n,]. Using unfiltered signal may cause unreliable results.
    aerial : `ndarray`
        Array of force signal measured at middle of each aerial phase.
    aerial_loc : `ndarray`
        Array of frame indexes for values in aerial. output from `aerialforce()`

    Returns
    -------
    force_fd : `ndarray`
        Array with shape of force_f, but with drift removed (detrended).

    Examples
    --------
        from dryft import signal

        force_fd = signal.detrend(force_f, aerial, aerial_loc)

    """

    # Create NaN array with aerial values at respective frame locations
    drift_signal = np.full(force_f.shape, np.nan)
    drift_signal[aerial_loc] = aerial
    # Use 3rd order spline to fill NaNs, creating the underlying drift of the signal.
    drift_signal_p = pd.Series(drift_signal)
    drift_signal_p = drift_signal_p.interpolate(method = 'spline', order = 3, s = 0, limit_direction= 'both')
    drift_signal = drift_signal_p.to_numpy()
    # Subtract drift from force signal
    force_fd = force_f - drift_signal

    return force_fd


def aerialforce(force, begin, end):
    """Calculate force signal at middle of aerial phase of running.

    Parameters
    ----------
    force : `ndarray`
        Filtered vertical ground reaction force (vGRF) signal [n,]. Using unfiltered signal will cause unreliable results.
    begin : `ndarray`
        Array of frame indexes for start of each stance phase.
    end : `ndarray`
        Array of frame indexes for end of each stance phase. Same size as `begin`.

    Returns
    -------
    aerial : `ndarray`
        Array containing force measured at middle of aerial phase force signal.
    aerial_loc : `ndarray`
        Array of frame indexes for values in aerial. output from `aerialforce()`

    """

    aerial_begin = end[:-1]
    aerial_end = begin[1:]

    # calculate force at middle of aerial phase (foot not on ground, should be zero)
    if force.ndim == 1:  # one axis only
        aerial = np.full([aerial_begin.shape[0], ], np.nan)
        aerial_middle = np.full([aerial_begin.shape[0], ], np.nan)

        for i in range(aerial.shape[0]):
            aerial_len = aerial_end-aerial_begin
            aerial_middle[i,] = round(aerial_len[i]/2)
            aerial[i,] = force[aerial_begin[i]+aerial_middle.astype(int)[i]]
        aerial_loc = aerial_begin + aerial_middle.astype(int)
    else: raise IndexError('force.ndim != 1')

    return aerial, aerial_loc




def splitsteps(vGRF, threshold, Fs, min_tc, max_tc, plot=False):
    """Read in filtered vertical ground reaction force (vGRF) signal and split steps based on a threshold.

    Designed for running, hopping, or activity where 1 foot is on the force plate at a time.
    Split steps are compared to min/max contact time (tc) to eliminate steps that are too short/long. Update these
    parameters and threshold if little-no steps are identified. Setting plots=True can aid in troubleshooting.

    Parameters
    ----------
    vGRF : `ndarray`
        Filtered vertical ground reaction force (vGRF) signal [n,]. Using unfiltered signal will cause unreliable results.
    threshold : `number`
        Determines when initial contact and final contact are defined. In the same units as vGRF signal. Please be
        responsible and set to < 50N for running data.
    Fs : `number`
        Sampling frequency of signal.
    min_tc : `number`
        Minimum contact time, in seconds, to consider as a real step. Jogging > 0.2s
    max_tc : number
        Maximum contact time, in seconds, to consider as a real step. Jogging > 0.4s
    plot : `bool`
        If true, return plot showing vGRF signal with initial and final contact points identified. Helpful for
        determining appropriate threshold, min_tc, and max_tc values.

    Returns
    -------
    step_begin : `ndarray`
        Array of frame indexes for start of stance phase.
    step_end : `ndarray`
        Array of frame indexes for end of stance phase.

    Examples
    --------
        from dryft import signal
        step_begin, step_end = signal.splitsteps(vGRF=GRF_filt[:,2],
                                             threshold=110,
                                             Fs=300,
                                             min_tc=0.2,
                                             max_tc=0.4,
                                             plot=False)
        step_begin
        step_end

    array([102, 215, 325])
    array([171, 285, 397])

    """

    if min_tc < max_tc:
        # step Identification Forces over step_threshold register as step (foot on ground).
        compare = (vGRF > threshold).astype(int)

        events = np.diff(compare)
        print(sum((compare)))
        step_begin_all = np.squeeze(np.asarray(np.nonzero(events == 1)).transpose())
        step_end_all = np.squeeze(np.asarray(np.nonzero(events == -1)).transpose())

        if plot:
            plt.plot(vGRF)
            plt.plot(events*500)
            plt.show(block = False)

        # if trial starts with end of step, ignore
        step_end_all = step_end_all[step_end_all > step_begin_all[0]]
        # trim end of step_begin_all to match step_end_all.
        step_begin_all = step_begin_all[0:step_end_all.shape[0]]

        # initialize
        # stance_len = np.full(step_begin_all.shape, np.nan)  # step begin and end should be same length...
        # step_begin = np.full(step_begin_all.shape, np.nan)
        # step_end = np.full(step_end_all.shape, np.nan)
        # calculate step length and compare to min/max step lengths

        stance_len = step_end_all - step_begin_all
        good_step = np.logical_and(stance_len >= min_tc*Fs, stance_len <= max_tc*Fs)

        step_begin = step_begin_all[good_step]
        step_end = step_end_all[good_step]
        # ID suspicious steps (too long or short)
        if np.any(stance_len < min_tc*Fs):
            print('Out of', stance_len.shape[0], 'stance phases,', sum(stance_len < min_tc*Fs), ' < ',
                  min_tc, 'seconds.')
        if np.any(stance_len > max_tc*Fs):
            print('Out of', stance_len.shape[0], 'stance_phases,', sum(stance_len > max_tc*Fs), ' > ',
                  max_tc, 'seconds.')
        # print sizes
        print('Number of contact time begin/end:', step_begin.shape[0], step_end.shape[0])

        return step_begin, step_end

    else:
        raise IndexError('Did not separate steps. min_tc > max_tc.')
