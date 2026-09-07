// SPDX-FileCopyrightText: 2025 Demerzel Solutions Limited
// SPDX-License-Identifier: LGPL-3.0-only

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Nethermind.Core.Timers;
using Nethermind.Logging;
using ITimer = Nethermind.Core.Timers.ITimer;

namespace Nethermind.Core.Scheduler;

/// <summary>
/// Manages periodic execution of registered <see cref="IScheduledTask"/> instances.
/// Each task is driven by a dedicated timer created via <see cref="ITimerFactory"/>.
/// </summary>
public sealed class CommandScheduler : ICommandScheduler
{
    private readonly ITimerFactory _timerFactory;
    private readonly ILogger _logger;
    private readonly List<IScheduledTask> _tasks = [];
    private readonly List<ITimer> _timers = [];
    private CancellationToken _cancellationToken;
    private bool _started;

    public CommandScheduler(ITimerFactory timerFactory, ILogManager logManager)
    {
        ArgumentNullException.ThrowIfNull(timerFactory);
        ArgumentNullException.ThrowIfNull(logManager);

        _timerFactory = timerFactory;
        _logger = logManager.GetClassLogger();
    }

    /// <inheritdoc/>
    public void Register(IScheduledTask task)
    {
        ArgumentNullException.ThrowIfNull(task);

        if (_started)
        {
            throw new InvalidOperationException($"Cannot register task '{task.Name}' after the scheduler has been started.");
        }

        _tasks.Add(task);
        if (_logger.IsDebug) _logger.Debug($"Registered scheduled task '{task.Name}' with interval {task.Interval}.");
    }

    /// <inheritdoc/>
    public void Start(CancellationToken cancellationToken = default)
    {
        if (_started)
        {
            throw new InvalidOperationException("The scheduler has already been started.");
        }

        _started = true;
        _cancellationToken = cancellationToken;

        foreach (IScheduledTask task in _tasks)
        {
            ITimer timer = _timerFactory.CreateTimer(task.Interval);
            timer.AutoReset = true;
            timer.Elapsed += (_, _) => OnTimerElapsed(task);
            timer.Start();
            _timers.Add(timer);

            if (_logger.IsInfo) _logger.Info($"Scheduled task '{task.Name}' started with interval {task.Interval}.");
        }
    }

    private void OnTimerElapsed(IScheduledTask task)
    {
        if (_cancellationToken.IsCancellationRequested)
        {
            return;
        }

        // Run the task on a thread-pool thread to avoid blocking the timer thread.
        // RunTaskAsync catches all exceptions, so the resulting task will not fault.
        Task runTask = Task.Run(() => RunTaskAsync(task, _cancellationToken), _cancellationToken);
        runTask.ContinueWith(
            t => { if (_logger.IsError) _logger.Error($"Unexpected failure in scheduled task '{task.Name}'.", t.Exception); },
            TaskContinuationOptions.OnlyOnFaulted);
    }

    private async Task RunTaskAsync(IScheduledTask task, CancellationToken cancellationToken)
    {
        try
        {
            await task.ExecuteAsync(cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Expected on shutdown.
        }
        catch (Exception ex)
        {
            if (_logger.IsError) _logger.Error($"Unhandled exception in scheduled task '{task.Name}'.", ex);
        }
    }

    /// <inheritdoc/>
    public ValueTask DisposeAsync()
    {
        foreach (ITimer timer in _timers)
        {
            timer.Stop();
            timer.Dispose();
        }

        _timers.Clear();
        return ValueTask.CompletedTask;
    }
}
