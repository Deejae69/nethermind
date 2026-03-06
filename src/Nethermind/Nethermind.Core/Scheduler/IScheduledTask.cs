// SPDX-FileCopyrightText: 2025 Demerzel Solutions Limited
// SPDX-License-Identifier: LGPL-3.0-only

using System;
using System.Threading;
using System.Threading.Tasks;

namespace Nethermind.Core.Scheduler;

/// <summary>
/// Represents a task that is executed periodically on a fixed interval.
/// </summary>
public interface IScheduledTask
{
    /// <summary>
    /// Gets the name identifying this scheduled task.
    /// </summary>
    string Name { get; }

    /// <summary>
    /// Gets the interval at which the task should be executed.
    /// </summary>
    TimeSpan Interval { get; }

    /// <summary>
    /// Executes the task asynchronously.
    /// </summary>
    /// <param name="cancellationToken">Token to observe for cancellation.</param>
    Task ExecuteAsync(CancellationToken cancellationToken);
}
