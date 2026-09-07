// SPDX-FileCopyrightText: 2025 Demerzel Solutions Limited
// SPDX-License-Identifier: LGPL-3.0-only

using System;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Nethermind.Core.Scheduler;
using Nethermind.Core.Timers;
using Nethermind.Logging;
using NSubstitute;
using NUnit.Framework;
using ITimer = Nethermind.Core.Timers.ITimer;

namespace Nethermind.Core.Test.Scheduler;

public class CommandSchedulerTests
{
    private ITimerFactory _timerFactory = null!;

    [SetUp]
    public void SetUp()
    {
        _timerFactory = TimerFactory.Default;
    }

    [Test]
    public async Task Registered_task_is_executed_on_timer_elapsed()
    {
        using ManualResetEventSlim executed = new(initialState: false);
        ITimer capturedTimer = null!;

        ITimerFactory factory = new FunctionalTimerFactory(interval =>
        {
            ITimer timer = Substitute.For<ITimer>();
            capturedTimer = timer;
            return timer;
        });

        await using CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);

        SimpleTask task = new SimpleTask("test-task", TimeSpan.FromSeconds(1), _ =>
        {
            executed.Set();
            return Task.CompletedTask;
        });

        scheduler.Register(task);
        scheduler.Start();

        // Simulate the timer firing
        capturedTimer.Elapsed += Raise.Event();

        executed.Wait(timeout: TimeSpan.FromSeconds(5)).Should().BeTrue("task should execute when timer elapses");
    }

    [Test]
    public async Task Multiple_tasks_each_get_their_own_timer()
    {
        int timerCount = 0;

        ITimerFactory factory = new FunctionalTimerFactory(_ =>
        {
            Interlocked.Increment(ref timerCount);
            return Substitute.For<ITimer>();
        });

        await using CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);

        scheduler.Register(new SimpleTask("task-1", TimeSpan.FromSeconds(1)));
        scheduler.Register(new SimpleTask("task-2", TimeSpan.FromSeconds(2)));
        scheduler.Register(new SimpleTask("task-3", TimeSpan.FromSeconds(3)));
        scheduler.Start();

        timerCount.Should().Be(3, "each registered task should get its own timer");
    }

    [Test]
    public void Cannot_register_after_start()
    {
        ITimerFactory factory = new FunctionalTimerFactory(_ => Substitute.For<ITimer>());

        CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);
        scheduler.Start();

        try
        {
            Action act = () => scheduler.Register(new SimpleTask("late-task", TimeSpan.FromSeconds(1)));

            act.Should().Throw<InvalidOperationException>()
                .WithMessage("*late-task*");
        }
        finally
        {
            _ = scheduler.DisposeAsync().AsTask();
        }
    }

    [Test]
    public void Cannot_start_twice()
    {
        ITimerFactory factory = new FunctionalTimerFactory(_ => Substitute.For<ITimer>());

        CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);
        scheduler.Start();

        try
        {
            Action act = () => scheduler.Start();
            act.Should().Throw<InvalidOperationException>();
        }
        finally
        {
            _ = scheduler.DisposeAsync().AsTask();
        }
    }

    [Test]
    public async Task Task_exception_does_not_crash_scheduler()
    {
        ITimer capturedTimer = null!;
        ITimerFactory factory = new FunctionalTimerFactory(_ =>
        {
            ITimer timer = Substitute.For<ITimer>();
            capturedTimer = timer;
            return timer;
        });

        await using CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);

        using ManualResetEventSlim faulted = new(initialState: false);
        SimpleTask task = new SimpleTask("faulting-task", TimeSpan.FromSeconds(1), _ =>
        {
            faulted.Set();
            throw new InvalidOperationException("task failure");
        });

        scheduler.Register(task);
        scheduler.Start();

        capturedTimer.Elapsed += Raise.Event();

        // The scheduler should absorb the exception and not crash
        faulted.Wait(TimeSpan.FromSeconds(5)).Should().BeTrue();
        // Give the error handler a moment to run
        await Task.Delay(50);
    }

    [Test]
    public async Task Dispose_stops_all_timers()
    {
        ITimer timer1 = Substitute.For<ITimer>();
        ITimer timer2 = Substitute.For<ITimer>();
        int call = 0;

        ITimerFactory factory = new FunctionalTimerFactory(_ =>
        {
            return Interlocked.Increment(ref call) == 1 ? timer1 : timer2;
        });

        CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);
        scheduler.Register(new SimpleTask("a", TimeSpan.FromSeconds(1)));
        scheduler.Register(new SimpleTask("b", TimeSpan.FromSeconds(2)));
        scheduler.Start();

        await scheduler.DisposeAsync();

        timer1.Received().Stop();
        timer1.Received().Dispose();
        timer2.Received().Stop();
        timer2.Received().Dispose();
    }

    [Test]
    public async Task Cancelled_token_prevents_task_execution()
    {
        ITimer capturedTimer = null!;
        ITimerFactory factory = new FunctionalTimerFactory(_ =>
        {
            ITimer timer = Substitute.For<ITimer>();
            capturedTimer = timer;
            return timer;
        });

        await using CommandScheduler scheduler = new CommandScheduler(factory, LimboLogs.Instance);

        bool executed = false;
        SimpleTask task = new SimpleTask("cancel-task", TimeSpan.FromSeconds(1), _ =>
        {
            executed = true;
            return Task.CompletedTask;
        });

        scheduler.Register(task);

        using CancellationTokenSource cts = new();
        scheduler.Start(cts.Token);
        cts.Cancel();

        capturedTimer.Elapsed += Raise.Event();

        // Give the timer callback a moment to run (it should bail out immediately)
        await Task.Delay(100);
        executed.Should().BeFalse("cancelled token should prevent task execution");
    }

    /// <summary>
    /// Minimal <see cref="IScheduledTask"/> for use in tests.
    /// </summary>
    private sealed class SimpleTask(
        string name,
        TimeSpan interval,
        Func<CancellationToken, Task>? action = null) : IScheduledTask
    {
        public string Name { get; } = name;
        public TimeSpan Interval { get; } = interval;

        public Task ExecuteAsync(CancellationToken cancellationToken) =>
            action is not null ? action(cancellationToken) : Task.CompletedTask;
    }
}
