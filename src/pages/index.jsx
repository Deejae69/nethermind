import { useState } from 'react'
import {
    ActionMenu,
    Avatar,
    Button,
    Heading,
    Label,
    Link,
    NavList,
    Stack,
    Text,
} from '@primer/react'
import {
    BellIcon,
    ChevronDownIcon,
    GraphIcon,
    HomeIcon,
    IssueOpenedIcon,
    MarkGithubIcon,
    RocketIcon,
    SearchIcon,
    GearIcon,
    StarIcon,
    ZapIcon,
} from '@primer/octicons-react'

import styles from './index.module.css'

const signals = [
    { pair: 'EUR/USD', direction: 'BUY', entry: '1.0842', target: '1.0910', stop: '1.0805', confidence: 92, age: '2m ago', tone: 'success' },
    { pair: 'GBP/JPY', direction: 'SELL', entry: '191.84', target: '190.55', stop: '192.42', confidence: 86, age: '8m ago', tone: 'danger' },
    { pair: 'USD/CAD', direction: 'BUY', entry: '1.3618', target: '1.3690', stop: '1.3575', confidence: 78, age: '14m ago', tone: 'success' },
    { pair: 'AUD/USD', direction: 'SELL', entry: '0.6574', target: '0.6510', stop: '0.6602', confidence: 71, age: '23m ago', tone: 'danger' },
]

const watchlist = [
    ['EUR/USD', '1.0842', '+0.42%', 'up'],
    ['GBP/USD', '1.2718', '-0.18%', 'down'],
    ['USD/JPY', '157.42', '+0.31%', 'up'],
    ['XAU/USD', '2,324.60', '+0.76%', 'up'],
]

function Metric({ label, value, detail, tone }) {
    return (
        <div className={styles.metric}>
            <Text color="fg.muted" size="small">{label}</Text>
            <Heading as="h2" className={styles.metricValue}>{value}</Heading>
            <Text size="small" className={tone === 'success' ? styles.success : styles.muted}>{detail}</Text>
        </div>
    )
}

function SignalCard({ signal, selected, onSelect }) {
    return (
        <button className={`${styles.signalCard} ${selected ? styles.selected : ''}`} onClick={onSelect} type="button">
            <div className={styles.signalTop}>
                <div className={styles.pairBlock}>
                    <span className={`${styles.directionDot} ${signal.tone === 'success' ? styles.dotSuccess : styles.dotDanger}`} />
                    <div>
                        <Text weight="semibold">{signal.pair}</Text>
                        <Text color="fg.muted" size="small" as="div">Momentum strategy · {signal.age}</Text>
                    </div>
                </div>
                <Label variant={signal.tone}>{signal.direction}</Label>
            </div>
            <div className={styles.signalNumbers}>
                <div><Text color="fg.muted" size="small" as="div">Entry</Text><Text weight="semibold">{signal.entry}</Text></div>
                <div><Text color="fg.muted" size="small" as="div">Target</Text><Text weight="semibold" className={styles.success}>{signal.target}</Text></div>
                <div><Text color="fg.muted" size="small" as="div">Stop</Text><Text weight="semibold" className={styles.danger}>{signal.stop}</Text></div>
            </div>
            <div className={styles.confidenceRow}>
                <Text color="fg.muted" size="small">Signal confidence</Text>
                <Text size="small" weight="semibold">{signal.confidence}%</Text>
            </div>
            <div className={styles.progressTrack}><div className={styles.progressFill} style={{ width: `${signal.confidence}%` }} /></div>
        </button>
    )
}

function Sidebar() {
    return (
        <aside className={styles.sidebar}>
            <div className={styles.brand}><div className={styles.brandMark}><ZapIcon size={18} /></div><Text weight="semibold" size="large">PipPilot</Text></div>
            <Text color="fg.muted" size="small" className={styles.eyebrow}>TRADING DESK</Text>
            <NavList>
                <NavList.Item selected icon={HomeIcon}>Overview</NavList.Item>
                <NavList.Item icon={GraphIcon}>Live signals <NavList.TrailingAction><Label variant="accent">4</Label></NavList.TrailingAction></NavList.Item>
                <NavList.Item icon={StarIcon}>Watchlist</NavList.Item>
                <NavList.Item icon={IssueOpenedIcon}>Trade journal</NavList.Item>
            </NavList>
            <Text color="fg.muted" size="small" className={styles.eyebrow}>WORKSPACE</Text>
            <NavList>
                <NavList.Item icon={RocketIcon}>Performance</NavList.Item>
                <NavList.Item icon={GearIcon}>Settings</NavList.Item>
            </NavList>
            <div className={styles.sidebarBottom}>
                <div className={styles.proCard}><div className={styles.proIcon}><RocketIcon size={16} /></div><Text weight="semibold" size="small">Pro workspace</Text><Text color="fg.muted" size="small">Unlock higher frequency alerts.</Text><Button size="small" variant="primary">Upgrade</Button></div>
                <div className={styles.user}><Avatar src="https://github.com/primer.png" size={32} /><div><Text weight="semibold" size="small">Alex Morgan</Text><Text color="fg.muted" size="small" as="div">Personal account</Text></div><ChevronDownIcon size={16} /></div>
            </div>
        </aside>
    )
}

function App() {
    const [selected, setSelected] = useState(0)
    const [filter, setFilter] = useState('All')
    const visibleSignals = filter === 'All' ? signals : signals.filter((signal) => signal.direction === filter.toUpperCase())
    return (
        <div className={styles.appShell}>
            <Sidebar />
            <main className={styles.main}>
                <header className={styles.topbar}><div><Text color="fg.muted" size="small">Monday, October 4, 2026</Text><Heading as="h1" className={styles.title}>Good morning, Alex</Heading></div><div className={styles.topActions}><Button leadingVisual={SearchIcon} aria-label="Search" /><Button leadingVisual={BellIcon} aria-label="Notifications" /><ActionMenu><ActionMenu.Button>UTC <ChevronDownIcon size={14} /></ActionMenu.Button><ActionMenu.Overlay><ActionMenu.Item>UTC</ActionMenu.Item><ActionMenu.Item>New York</ActionMenu.Item><ActionMenu.Item>London</ActionMenu.Item></ActionMenu.Overlay></ActionMenu></div></header>
                <div className={styles.marketBanner}><div className={styles.marketPulse}><span className={styles.liveDot} /> <Text weight="semibold" size="small">Markets open</Text><Text color="fg.muted" size="small">· London session</Text></div><Text color="fg.muted" size="small">Next major event <Text weight="semibold">US ISM Services</Text> in 01:42:18</Text></div>
                <section className={styles.metrics}><Metric label="Account balance" value="$24,680.40" detail="+$1,248.20 this month" tone="success" /><Metric label="Win rate" value="68.4%" detail="+4.2% vs last month" tone="success" /><Metric label="Active trades" value="3" detail="$482.60 unrealized P&L" /><Metric label="Risk exposure" value="2.8%" detail="Within your 4% limit" /></section>
                <div className={styles.contentGrid}>
                    <section className={styles.signalsSection}><div className={styles.sectionHeader}><div><Heading as="h2" className={styles.sectionTitle}>Live signals</Heading><Text color="fg.muted">AI-ranked setups based on momentum and market structure.</Text></div><ActionMenu><ActionMenu.Button>Sort: Confidence <ChevronDownIcon size={14} /></ActionMenu.Button><ActionMenu.Overlay><ActionMenu.Item>Confidence</ActionMenu.Item><ActionMenu.Item>Newest</ActionMenu.Item><ActionMenu.Item>Risk / reward</ActionMenu.Item></ActionMenu.Overlay></ActionMenu></div><div className={styles.filters}>{['All', 'Buy', 'Sell'].map((item) => <Button key={item} size="small" variant={filter === item ? 'primary' : 'invisible'} onClick={() => setFilter(item)}>{item}{item === 'All' ? ' · 4' : ''}</Button>)}</div><div className={styles.signalList}>{visibleSignals.map((signal, index) => <SignalCard key={signal.pair} signal={signal} selected={selected === index} onSelect={() => setSelected(index)} />)}</div></section>
                    <aside className={styles.rightRail}><section className={styles.panel}><div className={styles.panelHeader}><Heading as="h3">Selected signal</Heading><Label variant="success">High confidence</Label></div><div className={styles.selectedPair}><Text as="div" size="large" weight="semibold">{signals[selected].pair}</Text><Text className={signals[selected].tone === 'success' ? styles.success : styles.danger} weight="semibold">{signals[selected].direction} · {signals[selected].confidence}%</Text></div><div className={styles.chart}><div className={styles.chartGrid} /><svg viewBox="0 0 400 130" preserveAspectRatio="none" aria-label="EUR USD price trend"><path d="M0,98 C28,92 40,105 64,84 S95,88 116,76 S140,84 164,59 S198,70 220,50 S246,57 267,43 S291,55 314,32 S350,45 376,18 S392,25 400,13" fill="none" stroke="var(--fgColor-success)" strokeWidth="2.5" /><path d="M0,98 C28,92 40,105 64,84 S95,88 116,76 S140,84 164,59 S198,70 220,50 S246,57 267,43 S291,55 314,32 S350,45 376,18 S392,25 400,13 L400,130 L0,130 Z" fill="var(--bgColor-success-muted)" opacity=".35" /></svg></div><div className={styles.detailRows}><div><Text color="fg.muted" size="small">Entry</Text><Text weight="semibold">{signals[selected].entry}</Text></div><div><Text color="fg.muted" size="small">Target</Text><Text weight="semibold" className={styles.success}>{signals[selected].target}</Text></div><div><Text color="fg.muted" size="small">Stop loss</Text><Text weight="semibold" className={styles.danger}>{signals[selected].stop}</Text></div><div><Text color="fg.muted" size="small">Risk / reward</Text><Text weight="semibold">1 : 2.4</Text></div></div><Button variant="primary" block>Review trade setup</Button></section><section className={styles.panel}><div className={styles.panelHeader}><Heading as="h3">Market watchlist</Heading><Link href="#">View all</Link></div>{watchlist.map(([pair, price, change, trend]) => <div className={styles.watchRow} key={pair}><div className={styles.watchPair}><span className={`${styles.tinyTrend} ${trend === 'up' ? styles.dotSuccess : styles.dotDanger}`} /><Text weight="semibold" size="small">{pair}</Text></div><Text size="small">{price}</Text><Text size="small" className={trend === 'up' ? styles.success : styles.danger}>{change}</Text></div>)}</section></aside>
                </div>
                <footer className={styles.footer}><Text color="fg.muted" size="small">PipPilot uses algorithmic analysis, not financial advice.</Text><div><Link href="#">Documentation</Link><Link href="#">Status</Link><Link href="#">Support</Link></div></footer>
            </main>
        </div>
    )
}

export default App
        
