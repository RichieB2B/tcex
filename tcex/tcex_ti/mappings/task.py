# -*- coding: utf-8 -*-
"""ThreatConnect TI Adversary """
from tcex.tcex_ti.mappings.tcex_ti_mappings import TIMappings


class Task(TIMappings):
    """Unique API calls for Adversary API Endpoints"""

    def __init__(self, tcex, name, status, due_date, reminder_date, escalation_date, **kwargs):
        """Initialize Class Properties.

        Args:
            name (str): The name for this Group.
        """
        super(Task, self).__init__(tcex, 'Task', 'tasks', None, 'task')
        self._data['name'] = name
        if status:
            self._data['status'] = status
        if due_date:
            self._data['dueDate'] = due_date
        if reminder_date:
            self._data['reminderDate'] = reminder_date
        if escalation_date:
            self._data['escalationDate'] = escalation_date

        for arg, value in kwargs.items():
            self.add_key_value(arg, value)

    def status(self, status):
        self._data['status'] = status
        request = {'status': status}
        return self.tc_requests.update(self.api_type, self.api_sub_type, self.unique_id, request)

    def due_date(self, due_date):
        """Return Email to."""
        due_date = self._utils.format_datetime(due_date, date_format='%Y-%m-%dT%H:%M:%SZ')
        self._data['dueDate'] = due_date
        request = {'dueDate': due_date}
        return self.tc_requests.update(self.api_type, self.api_sub_type, self.unique_id, request)

    def reminder_date(self, reminder_date):
        """Return Email to."""
        reminder_date = self._utils.format_datetime(reminder_date, date_format='%Y-%m-%dT%H:%M:%SZ')
        self._data['reminderDate'] = reminder_date
        request = {'reminderDate': reminder_date}
        return self.tc_requests.update(self.api_type, self.api_sub_type, self.unique_id, request)

    def escalation_date(self, escalation_date):
        """Return Email to."""
        escalation_date = self._utils.format_datetime(escalation_date,
                                                      date_format='%Y-%m-%dT%H:%M:%SZ')
        self._data['escalationDate'] = escalation_date
        request = {'escalationDate': escalation_date}
        return self.tc_requests.update(self.api_type, self.api_sub_type, self.unique_id, request)

    def assignees(self):
        if not self.can_update():
            return

        yield from self.tc_requests.assignees(self.api_type, self.api_sub_type, self.unique_id)

    def assignee(self, assignee_id, action='ADD'):
        if not self.can_update():
            return

        return self.tc_requests.assignee(self.api_type, self.api_sub_type, self.unique_id,
                                             assignee_id, action=action)

    def add_assignee(self, assignee_id):
        return self.assignee(assignee_id)

    def get_assignee(self, assignee_id):
        return self.assignee(assignee_id, action='GET')

    def delete_assignee(self, assignee_id):
        return self.assignee(assignee_id, action='DELETE')

    def escalatees(self):
        if not self.can_update():
            return

        yield from self.tc_requests.escalatees(self.api_type, self.api_sub_type, self.unique_id)

    def escalatee(self, escalatee_id, action='ADD'):
        if not self.can_update():
            return

        return self.tc_requests.escalatee(self.api_type, self.api_sub_type, self.unique_id,
                                             escalatee_id, action=action)

    def add_escalatee(self, escalatee_id):
        return self.assignee(escalatee_id)

    def get_escalatee(self, escalatee_id):
        return self.assignee(escalatee_id, action='GET')

    def delete_escalatee(self, escalatee_id):
        return self.assignee(escalatee_id, action='DELETE')

    def add_key_value(self, key, value):
        """

        :param key:
        :param value:
        """
        self._data[key] = value

