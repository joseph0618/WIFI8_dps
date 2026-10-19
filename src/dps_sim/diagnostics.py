"""Optional streaming diagnostics; no random draws or access-policy changes."""
from collections import Counter, defaultdict
import math

class ContentionDiagnostics:
    def __init__(self, bin_seconds=1.0, prefix_events=1000):
        if bin_seconds <= 0: raise ValueError('Positive bin width required')
        self.bin_us = bin_seconds*1e6
        self.prefix_limit = prefix_events
        self.prefix = []
        self.bins = defaultdict(Counter)
        self.attempts = Counter()
        self.collided = Counter()
        self.components = Counter()
        self.frames = Counter()
        self.frame_airtime_us = Counter()
        self.pending_reports = {}
        self.pairs = []
        self.occupancy_us = Counter()
        self.events = 0
        self.collision_events = 0
        self.first_prefix_attempts = self.first_prefix_collided = None

    def observe_time(self, start_us, duration_us, reported):
        self.occupancy_us[reported] += duration_us
        finish = start_us+duration_us
        while start_us < finish-1e-9:
            idx = int(start_us/self.bin_us)
            stop = min(finish,(idx+1)*self.bin_us)
            if stop <= start_us: break
            self.bins[idx]['observed_us'] += stop-start_us
            self.bins[idx]['reported_sta_us'] += reported*(stop-start_us)
            start_us=stop

    def observe_event(self, event):
        self.events += 1
        roles=event['roles']
        collision=len(roles)>1
        outcome='collision' if collision else 'success'
        b=self.bins[int(event['start_us']/self.bin_us)]
        b['events']+=1
        b['attempts']+=len(roles)
        b['collided_attempts']+=len(roles) if collision else 0
        if collision:
            self.collision_events += 1
            b['collision_events']+=1
        for role in roles:
            self.attempts[role]+=1
            self.collided[role]+=int(collision)
            self.components[outcome+'_'+role]+=1
        if len(self.prefix)<self.prefix_limit:
            self.prefix.append((tuple(event['senders']),tuple(roles)))
            if len(self.prefix)==self.prefix_limit:
                self.first_prefix_attempts=sum(self.attempts.values())
                self.first_prefix_collided=sum(self.collided.values())
        # Snapshot frames before the current exchange to exclude the tagged endpoint.
        frames_before=self.frames.copy()
        if collision:
            self.frames['COLLISION'] += len(roles)
        for frame in event['frames']:
            observed=max(0.,min(frame['end_us'],event['horizon_us'])-frame['start_us'])
            if observed<=0: continue
            name=frame['name']
            if name != 'COLLISION':
                self.frames[name]+=len(frame['senders'])
            self.frame_airtime_us[name]+=observed*len(frame['senders'])
        if not event['success_completed']: return
        role=roles[0]
        if role=='EBSR':
            sta=event['senders'][0]
            self.pending_reports[sta]=dict(components=self.components.copy(),frames=self.frames.copy(),
                events=self.events,start_us=event['start_us'],ahead=event['reported'],
                bin_index=int(event['start_us']/self.bin_us))
        elif role=='ICF':
            sta=event['target']
            report=self.pending_reports.pop(sta)
            component=self.components-report['components']
            component['success_ICF']-=1
            frame_counts=frames_before-report['frames']
            pair=dict(start_us=report['start_us'],trigger_us=event['start_us'],
                      wait_ms=(event['start_us']-report['start_us'])/1000,
                      reports_ahead=report['ahead'],
                      intervening_events=self.events-report['events']-1,
                      intervening_attempts=sum(component.values()),
                      **{'attempt_'+k:component[k] for k in (
                          'success_EBSR','success_ICF','success_DATA','success_RTS',
                          'collision_EBSR','collision_ICF','collision_DATA','collision_RTS')},
                      **{'frame_'+k:frame_counts[k] for k in ('EBSR','ICF','ICR','DATA','ACK','RTS','CTS','COLLISION')})
            self.pairs.append(pair)
            b['completed_pairs']+=1

    def time_rows(self, duration_s):
        rows=[]; attempts=collided=events=0
        for idx in range(math.ceil(duration_s*1e6/self.bin_us)):
            b=self.bins[idx]
            attempts+=b['attempts'];collided+=b['collided_attempts'];events+=b['collision_events']
            width=min(self.bin_us,duration_s*1e6-idx*self.bin_us)/1e6
            rows.append(dict(start_s=idx*self.bin_us/1e6,end_s=idx*self.bin_us/1e6+width,
                attempts=b['attempts'],collided_attempts=b['collided_attempts'],
                collision_events=b['collision_events'],
                window_collision_ratio=b['collided_attempts']/b['attempts'] if b['attempts'] else math.nan,
                cumulative_collision_ratio=collided/attempts if attempts else math.nan,
                collision_events_per_second=b['collision_events']/width,
                mean_reported_stas=b['reported_sta_us']/b['observed_us'] if b['observed_us'] else math.nan))
        return rows
