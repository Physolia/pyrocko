# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------

from __future__ import absolute_import, print_function, division

import vtk

from pyrocko.guts import Bool, List, String, StringChoice, Float, get_elements
from pyrocko.gui.qt_compat import qw, qc
from pyrocko import util


from .base import Element, ElementState
from .. import common

guts_prefix = 'sparrow'


class HudPositionChoice(StringChoice):
    choices = ['bottom', 'bottom-left', 'bottom-right',
               'top', 'top-left', 'top-right']


class HudState(ElementState):
    visible = Bool.T(default=True)
    variables = List.T(String.T(optional=True))
    template = String.T()
    position = HudPositionChoice.T(default='bottom')
    lightness = Float.T(default=1.0)
    fontsize = Float.T(default=0.05)

    def create(self):
        return HudElement()


def none_or(f):
    def g(x):
        if x is None:
            return ''
        else:
            return f(x)

    return g


class Stringer(object):
    def __init__(self, d):
        self._d = d
        self._formatters = {
            'date': none_or(lambda v: util.time_to_str(v, format='%Y-%m-%d')),
            'datetime': none_or(lambda v: util.time_to_str(v))}

    def __getitem__(self, key):
        key = key.split('|', 1)
        if len(key) == 2:
            key, formatter = key[0], self._formatters.get(key[1], str)
        else:
            key, formatter = key[0], str

        if key in self._d:
            return formatter(self._d[key])
        else:
            return '{' + key + '}'


class HudElement(Element):

    def __init__(self):
        Element.__init__(self)
        self._text_actor = None
        self._listeners2 = []

    def get_name(self):
        return 'HUD'

    def get_state_listeners(self):
        return [
            (self.update, [
                'visible', 'lightness', 'fontsize', 'template', 'position']),
            (self.update_bindings, [
                'variables'])]

    def get_parent_state_listeners(self):
        return [(self.update, ['size'])]

    def update_bindings(self, *args):
        while self._listeners2:
            listener_ref = self._listeners2.pop()
            listener_ref.release()

        for variable in self._state.variables:
            self._listeners2.append(
                self._parent.state.add_listener(self.update, variable))

    def update(self, *args):
        state = self._state
        if not self._state:
            return
        pstate = self._parent.state

        if self._text_actor is None:
            self._text_actor = vtk.vtkTextActor()

        actor = self._text_actor

        vs = [
            get_elements(pstate, variable)[0]
            for variable in self._state.variables]

        s = Stringer(d=dict((str(i), v) for (i, v) in enumerate(vs)))
        actor.SetInput(self._state.template.format_map(s))

        sx, sy = self._parent.gui_state.size
        cx = 0.5 * sx
        # cy = 0.5 * sy
        off = 0.1 * sy
        pos = {
            'top': (cx, sy - off, 1, 2),
            'top-left': (off, sy - off, 0, 2),
            'top-right': (sx - off, sy - off, 2, 2),
            'bottom': (cx, off, 1, 0),
            'bottom-left': (off, off, 0, 0),
            'bottom-right': (sx - off, off, 2, 0)}
        x, y, hj, vj = pos[state.position]

        actor.SetPosition(x, y)
        prop = actor.GetTextProperty()
        prop.SetFontSize(int(round(state.fontsize*sy)))

        lightness = state.lightness
        prop.SetColor(lightness*0.8, lightness*0.8, lightness*0.7)
        prop.SetJustification(hj)
        prop.SetVerticalJustification(vj)

        if state.visible:
            self.add_actor_2d(actor)
        else:
            self.remove_actor_2d(actor)

        self._parent.update_view()

    def get_panel(self):
        from ..state import state_bind_checkbox, state_bind_lineedit, \
            state_bind_combobox, state_bind_slider

        frame = qw.QFrame()
        layout = qw.QGridLayout()
        frame.setLayout(layout)

        layout.addWidget(qw.QLabel('Template'), 0, 0)
        le = qw.QLineEdit()
        layout.addWidget(le, 0, 1)
        state_bind_lineedit(self, self._state, 'template', le)

        cb = qw.QCheckBox('Show')
        layout.addWidget(cb, 1, 0)
        state_bind_checkbox(self, self._state, 'visible', cb)

        cb = common.string_choices_to_combobox(HudPositionChoice)
        layout.addWidget(qw.QLabel('Position'), 2, 0)
        layout.addWidget(cb, 2, 1)
        state_bind_combobox(self, self._state, 'position', cb)

        layout.addWidget(qw.QLabel('Lightness'), 3, 0)

        slider = qw.QSlider(qc.Qt.Horizontal)
        slider.setSizePolicy(
            qw.QSizePolicy(
                qw.QSizePolicy.Expanding, qw.QSizePolicy.Fixed))
        slider.setMinimum(0)
        slider.setMaximum(1000)
        layout.addWidget(slider, 3, 1)

        state_bind_slider(
            self, self._state, 'lightness', slider, factor=0.001)

        layout.addWidget(qw.QLabel('Fontsize'), 4, 0)

        slider = qw.QSlider(qc.Qt.Horizontal)
        slider.setSizePolicy(
            qw.QSizePolicy(
                qw.QSizePolicy.Expanding, qw.QSizePolicy.Fixed))
        slider.setMinimum(0)
        slider.setMaximum(1000)
        layout.addWidget(slider, 4, 1)

        state_bind_slider(
            self, self._state, 'fontsize', slider, factor=0.001)

        layout.addWidget(qw.QFrame(), 5, 0)

        return frame


__all__ = [
    'HudElement',
    'HudState']
