import React, { useEffect, useState, useCallback } from 'react';
import {
  CalendarDays, Plus, Trash2, Sun, GraduationCap, AlertTriangle,
  ChevronLeft, ChevronRight, Info
} from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';

interface CalendarEvent {
  id: number;
  event_date: string;
  label: string;
  event_type: 'holiday' | 'exam_day';
  affects_ordering: boolean;
  description: string | null;
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function HolidayCalendar() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);

  // Form state
  const [formDate, setFormDate] = useState('');
  const [formLabel, setFormLabel] = useState('');
  const [formType, setFormType] = useState<'holiday' | 'exam_day'>('holiday');
  const [formAffectsOrdering, setFormAffectsOrdering] = useState(true);
  const [formDescription, setFormDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getCalendarEvents({ year, month });
      setEvents(res.data.events ?? []);
    } catch {
      toast.error('Failed to load calendar events');
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  const prevMonth = () => {
    if (month === 1) { setYear(y => y - 1); setMonth(12); }
    else { setMonth(m => m - 1); }
  };

  const nextMonth = () => {
    if (month === 12) { setYear(y => y + 1); setMonth(1); }
    else { setMonth(m => m + 1); }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formDate || !formLabel.trim()) {
      toast.error('Date and label are required');
      return;
    }
    setSaving(true);
    try {
      const res = await adminApi.createCalendarEvent({
        event_date: formDate,
        label: formLabel.trim(),
        event_type: formType,
        affects_ordering: formAffectsOrdering,
        description: formDescription.trim() || null,
      });
      setEvents(prev => [...prev, res.data].sort(
        (a, b) => a.event_date.localeCompare(b.event_date)
      ));
      setShowForm(false);
      setFormDate('');
      setFormLabel('');
      setFormType('holiday');
      setFormAffectsOrdering(true);
      setFormDescription('');
      toast.success(`${formType === 'holiday' ? 'Holiday' : 'Exam day'} added`);
    } catch {
      toast.error('Failed to create event');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await adminApi.deleteCalendarEvent(id);
      setEvents(prev => prev.filter(e => e.id !== id));
      toast.success('Event removed');
    } catch {
      toast.error('Failed to delete event');
    }
  };

  // Build calendar grid
  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const todayStr = new Date().toISOString().slice(0, 10);

  const eventMap = new Map<string, CalendarEvent>();
  events.forEach(e => eventMap.set(e.event_date, e));

  const calendarDays: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) calendarDays.push(null);
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
          <CalendarDays className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-[#111827]">Holiday & Exam Calendar</h3>
          <p className="text-xs text-[#6B7280]">
            Mark dates as holidays (ordering closed) or exam days (faculty-only)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Calendar */}
        <div className="lg:col-span-2 tnt-card">
          {/* Month navigation */}
          <div className="flex items-center justify-between mb-4">
            <button onClick={prevMonth} className="btn-ghost btn-sm">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <h4 className="text-sm font-bold text-[#111827]">
              {MONTHS[month - 1]} {year}
            </h4>
            <button onClick={nextMonth} className="btn-ghost btn-sm">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 gap-1 mb-1">
            {DAYS.map(d => (
              <div key={d} className="text-center text-[10px] font-semibold text-[#6B7280] uppercase py-1">
                {d}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          {loading ? (
            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: 35 }).map((_, i) => (
                <div key={i} className="skeleton aspect-square rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-1">
              {calendarDays.map((d, i) => {
                if (d === null) return <div key={`empty-${i}`} />;
                const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                const event = eventMap.get(dateStr);
                const isToday = dateStr === todayStr;

                return (
                  <div
                    key={dateStr}
                    className={`relative aspect-square rounded-lg border flex flex-col items-center justify-center text-xs transition-all cursor-default
                      ${isToday ? 'border-[#E85D24] ring-1 ring-[#E85D24]/30' : 'border-[#E5E7EB]'}
                      ${event?.event_type === 'holiday' ? 'bg-red-500/10 border-red-500/30' : ''}
                      ${event?.event_type === 'exam_day' ? 'bg-amber-500/10 border-amber-500/30' : ''}
                      ${!event ? 'bg-white hover:bg-[#F9FAFB]' : ''}
                    `}
                    title={event ? `${event.label} (${event.event_type})` : undefined}
                  >
                    <span className={`font-semibold ${isToday ? 'text-[#E85D24]' : 'text-[#111827]'}`}>
                      {d}
                    </span>
                    {event && (
                      <div className={`w-1.5 h-1.5 rounded-full mt-0.5
                        ${event.event_type === 'holiday' ? 'bg-red-500' : 'bg-amber-500'}`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-4 mt-3 text-[10px] text-[#6B7280]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" /> Holiday
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" /> Exam Day
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#E85D24]" /> Today
            </span>
          </div>
        </div>

        {/* Side panel */}
        <div className="space-y-4">
          {/* Add button */}
          <button
            onClick={() => setShowForm(!showForm)}
            className="btn-primary w-full"
          >
            <Plus className="w-4 h-4" />
            {showForm ? 'Cancel' : 'Add Event'}
          </button>

          {/* Add form */}
          {showForm && (
            <div className="tnt-card">
              <h4 className="text-sm font-semibold text-[#111827] mb-3">New Event</h4>
              <form onSubmit={handleCreate} className="space-y-3">
                <div>
                  <label className="tnt-label">Date</label>
                  <input
                    type="date"
                    value={formDate}
                    onChange={e => setFormDate(e.target.value)}
                    className="tnt-input"
                    required
                  />
                </div>
                <div>
                  <label className="tnt-label">Label</label>
                  <input
                    type="text"
                    value={formLabel}
                    onChange={e => setFormLabel(e.target.value)}
                    placeholder="e.g. Diwali, Mid-Sem Exams"
                    className="tnt-input"
                    maxLength={200}
                    required
                  />
                </div>
                <div>
                  <label className="tnt-label">Type</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setFormType('holiday')}
                      className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-all flex items-center justify-center gap-1.5
                        ${formType === 'holiday'
                          ? 'bg-red-500/10 border-red-500/30 text-red-400'
                          : 'border-[#E5E7EB] text-[#6B7280]'}`}
                    >
                      <Sun className="w-3.5 h-3.5" /> Holiday
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormType('exam_day')}
                      className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-all flex items-center justify-center gap-1.5
                        ${formType === 'exam_day'
                          ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                          : 'border-[#E5E7EB] text-[#6B7280]'}`}
                    >
                      <GraduationCap className="w-3.5 h-3.5" /> Exam Day
                    </button>
                  </div>
                </div>
                <div>
                  <label className="tnt-label">Affects Ordering</label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formAffectsOrdering}
                      onChange={e => setFormAffectsOrdering(e.target.checked)}
                      className="accent-[#E85D24]"
                    />
                    <span className="text-xs text-[#4B5563]">
                      Block or restrict ordering on this date
                    </span>
                  </label>
                </div>
                <div>
                  <label className="tnt-label">Description (optional)</label>
                  <textarea
                    value={formDescription}
                    onChange={e => setFormDescription(e.target.value)}
                    placeholder="Brief note about this date..."
                    rows={2}
                    className="tnt-input resize-none"
                  />
                </div>
                <button
                  type="submit"
                  disabled={saving || !formDate || !formLabel.trim()}
                  className="btn-primary w-full"
                >
                  {saving ? 'Adding...' : 'Add to Calendar'}
                </button>
              </form>
            </div>
          )}

          {/* Events this month */}
          <div>
            <h4 className="text-sm font-semibold text-[#111827] mb-2">
              Events in {MONTHS[month - 1]}
              <span className="ml-1.5 text-[#6B7280] font-normal">({events.length})</span>
            </h4>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => <div key={i} className="skeleton h-14 rounded-lg" />)}
                </div>
              ) : events.length === 0 ? (
                <div className="text-center py-6 text-[#6B7280] text-xs">
                  No events this month
                </div>
              ) : (
                events.map(event => (
                  <div key={event.id} className="tnt-card !p-3 flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5
                      ${event.event_type === 'holiday' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                      {event.event_type === 'holiday' ? <Sun className="w-4 h-4" /> : <GraduationCap className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold text-[#111827] truncate">{event.label}</p>
                          <p className="text-[10px] text-[#6B7280] font-mono">
                            {new Date(event.event_date + 'T00:00:00').toLocaleDateString('en-IN', {
                              weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'
                            })}
                          </p>
                        </div>
                        <button
                          onClick={() => handleDelete(event.id)}
                          className="text-red-400 hover:text-red-300 shrink-0"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      {event.description && (
                        <p className="text-[10px] text-[#4B5563] mt-0.5">{event.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full uppercase
                          ${event.event_type === 'holiday'
                            ? 'bg-red-500/10 text-red-400'
                            : 'bg-amber-500/10 text-amber-400'}`}>
                          {event.event_type === 'holiday' ? 'Holiday' : 'Exam'}
                        </span>
                        <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full
                          ${event.affects_ordering
                            ? 'bg-[#E85D24]/10 text-[#E85D24]'
                            : 'bg-[#F3F5F9] text-[#6B7280]'}`}>
                          {event.affects_ordering ? 'Blocks orders' : 'Informational'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Info box */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 flex gap-3 text-xs text-blue-300">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold mb-1">How it works</p>
              <ul className="list-disc pl-4 space-y-1 text-blue-300/80">
                <li><strong>Holiday</strong> — Ordering is completely blocked for all users</li>
                <li><strong>Exam Day</strong> — Only faculty/staff can book slots; capacity is halved</li>
                <li>Toggle <em>Affects Ordering</em> off to make informational entries</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
