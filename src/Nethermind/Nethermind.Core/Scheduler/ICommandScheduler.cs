// SPDX-FileCopyrightText: 2025 Demerzel Solutions Limited
// SPDX-License-Identifier: LGPL-3.0-only

using System;
using System.Threading;
using System.Threading.Tasks;

namespace Nethermind.Core.Scheduler;

/// <summary>
/// Schedules and manages periodic execution of <see cref="IScheduledTask"/> instances.
/// </summary>
public interface ICommandScheduler : IAsyncDisposable
{
    /// <summary>
    /// Registers a task to be executed at its specified interval.
    /// </summary>
    /// <param name="task">The task to schedule.</param>
    void Register(IScheduledTask task);

    /// <summary>
    /// Starts all registered scheduled tasks.
    /// </summary>
    /// <param name="cancellationToken">Token to observe for cancellation.</param>
    void Start(CancellationToken cancellationToken = default);
}
