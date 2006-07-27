# Zeobuilder is an extensible GUI-toolkit for molecular model construction.
# Copyright (C) 2005 Toon Verstraelen
#
# This file is part of Zeobuilder.
#
# Zeobuilder is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# --


from zeobuilder import context
from zeobuilder.nodes.helpers import BoundingBox
from zeobuilder.nodes.meta import NodeClass, PublishedProperties, Property, DialogFieldInfo
from zeobuilder.nodes.analysis import common_parent
from zeobuilder.transformations import Translation, Rotation, Complete
import zeobuilder.gui.fields as fields

from OpenGL.GL import *
import gobject, numpy

import copy


__all__ = ["GLMixinError", "GLMixin", "GLTransformationMixin"]


class GLMixinError(Exception):
    pass


class GLMixin(gobject.GObject):

    __metaclass__ = NodeClass
    double_sided = False

    #
    # State
    #

    def initnonstate(self):
        self.gl_active = 0

    #
    # Properties
    #

    def set_visible(self, visible):
        if self.visible != visible:
            self.visible = visible
            self.invalidate_total_list()

    published_properties = PublishedProperties({
        "visible": Property(True, lambda self: self.visible, set_visible)
    })

    #
    # Dialog fields (see action EditProperties)
    #

    dialog_fields = set([
        DialogFieldInfo("Markup", (1, 2), fields.edit.CheckButton(
            label_text="Visible (also hides children)",
            attribute_name="visible",
        )),
        DialogFieldInfo("Basic", (0, 3), fields.read.BBox(
            label_text="Bounding box",
            attribute_name="bounding_box",
        )),
    ])

    #
    # OpenGL
    #

    def request_gl(self):
        self.gl_active += 1
        ##print "Request GL (active=%i): %s" % (self.gl_active, self.get_name())
        if self.gl_active == 1:
            self.initialize_gl()

    def drop_gl(self):
        self.gl_active -= 1
        ##print "Release GL (active=%i): %s" % (self.gl_active, self.get_name())
        if self.gl_active == 0:
            self.cleanup_gl()
        elif self.gl_active < 0:
            raise GLMixinError("request_gl and drop_gl must be called pairwise.")

    def initialize_gl(self):
        self.bounding_box = BoundingBox()

        self.draw_list = glGenLists(3)
        self.boundingbox_list = self.draw_list + 1
        self.total_list = self.draw_list + 2
        ##print "Created lists (%i, %i, %i): %s" % (self.draw_list, self.boundingbox_list, self.total_list, self.get_name())
        context.application.main.drawing_area.scene.gl_names[self.draw_list] = self
        self.draw_list_valid = True
        self.boundingbox_list_valid = True
        self.total_list_valid = True
        self.invalidate_all_lists()
        if isinstance(self.parent, GLMixin):
            self.parent.invalidate_all_lists()

    def cleanup_gl(self):
        del context.application.main.drawing_area.scene.gl_names[self.draw_list]
        ##print "Deleting lists (%i, %i, %i): %s" % (self.draw_list, self.boundingbox_list, self.total_list, self.get_name())
        glDeleteLists(self.draw_list, 3)
        del self.bounding_box
        del self.draw_list
        del self.boundingbox_list
        del self.total_list
        del self.draw_list_valid
        del self.boundingbox_list_valid
        del self.total_list_valid
        if isinstance(self.parent, GLMixin):
            self.parent.invalidate_all_lists()


    #
    # Invalidation
    #

    def invalidate_draw_list(self):
        if self.gl_active > 0 and self.draw_list_valid:
            self.draw_list_valid = False
            context.application.main.drawing_area.queue_draw()
            context.application.main.drawing_area.scene.add_revalidation(self.revalidate_draw_list)
            self.emit("on-draw-list-invalidated")
            ##print "EMIT %s: on-draw-list-invalidated" % self.get_name()
            if isinstance(self.parent, GLMixin):
                self.parent.invalidate_boundingbox_list()


    def invalidate_boundingbox_list(self):
        if self.gl_active > 0 and self.boundingbox_list_valid:
            self.boundingbox_list_valid = False
            context.application.main.drawing_area.queue_draw()
            context.application.main.drawing_area.scene.add_revalidation(self.revalidate_boundingbox_list)
            self.emit("on-boundingbox-list-invalidated")
            ##print "EMIT %s: on-boundingbox-list-invalidated"  % self.get_name()
            if isinstance(self.parent, GLMixin):
                self.parent.invalidate_boundingbox_list()

    def invalidate_total_list(self):
        if self.gl_active > 0 and self.total_list_valid:
            self.total_list_valid = False
            context.application.main.drawing_area.queue_draw()
            context.application.main.drawing_area.scene.add_revalidation(self.revalidate_total_list)
            self.emit("on-total-list-invalidated")
            ##print "EMIT %s: on-total-list-invalidated" % self.get_name()
            if isinstance(self.parent, GLMixin):
                self.parent.invalidate_boundingbox_list()

    def invalidate_all_lists(self):
        self.invalidate_total_list()
        self.invalidate_boundingbox_list()
        self.invalidate_draw_list()

    #
    # Revalidation
    #

    def revalidate_draw_list(self):
        if self.gl_active > 0:
            ##print "Compiling draw list (%i): %s" % (self.draw_list, self.get_name())
            glNewList(self.draw_list, GL_COMPILE)
            self.prepare_draw()
            self.draw()
            self.finish_draw()
            glEndList()
            self.draw_list_valid = True

    def revalidate_boundingbox_list(self):
        if self.gl_active > 0:
            ##print "Compiling selection list (%i): %s" % (self.boundingbox_list, self.get_name())
            glNewList(self.boundingbox_list, GL_COMPILE)
            self.revalidate_bounding_box()
            self.bounding_box.draw()
            glEndList()
            self.boundingbox_list_valid = True

    def revalidate_bounding_box(self):
        self.bounding_box.clear()

    def revalidate_total_list(self):
        if self.gl_active > 0:
            ##print "Compiling total list (%i): %s" % (self.total_list, self.get_name())
            glNewList(self.total_list, GL_COMPILE)
            if self.visible:
                glPushName(self.draw_list)
                if self.selected: glCallList(self.boundingbox_list)
                #if self.double_sided:
                #    glCullFace(GL_FRONT)
                glCallList(self.draw_list)
                #if self.double_sided:
                #    glCullFace(GL_BACK)
                #    glCallList(self.draw_list)
                glPopName()
            glEndList()
            self.total_list_valid = True

    #
    # Draw
    #

    def call_list(self):
        ##print "Executing total list (%i): %s" % (self.total_list, self.get_name())
        glCallList(self.total_list)

    def prepare_draw(self):
        pass

    def draw(self):
        pass

    def finish_draw(self):
        pass

    def write_pov(self, indenter):
        indenter.write_line("finish { my_finish }")

    #
    # Frame
    #

    def get_bounding_box_in_parent_frame(self):
        return self.bounding_box

    def get_absolute_frame(self):
        return self.get_absolute_parentframe()

    def get_absolute_parentframe(self):
        if not isinstance(self.parent, GLMixin):
            return Complete()
        else:
            return self.parent.get_absolute_frame()

    def get_frame_up_to(self, upper_parent):
        if (upper_parent == self) or (self.parent == upper_parent):
            return Complete()
        else:
            return self.get_parentframe_up_to(upper_parent)

    def get_parentframe_up_to(self, upper_parent):
        if not isinstance(self.parent, GLMixin):
            assert upper_parentisNone, "upper_parent must be (an indirect) parent of self."
            return Complete()
        elif self.parent == upper_parent:
            return Complete()
        else:
            return self.parent.get_frame_up_to(upper_parent)

    def get_frame_relative_to(self, other):
        common = common_parent([self, other])
        temp = self.get_frame_up_to(common)
        temp.apply_inverse_after(other.get_frame_up_to(common))
        return temp

    #
    # Flags
    #

    def set_selected(self, selected):
        if selected != self.selected:
            assert self.model is not None, "Can only select a node if it is part of a model."
            self.selected = selected
            self.invalidate_total_list()

gobject.signal_new("on-draw-list-invalidated", GLMixin, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
gobject.signal_new("on-boundingbox-list-invalidated", GLMixin, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
gobject.signal_new("on-total-list-invalidated", GLMixin, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())


class GLTransformationMixin(GLMixin):

    #
    # State
    #

    def initnonstate(self, Transformation):
        GLMixin.initnonstate(self)
        self.Transformation = Transformation

    #
    # Properties
    #

    def default_transformation(self):
        return self.Transformation()

    def set_transformation(self, transformation):
        self.transformation = transformation
        self.invalidate_transformation_list()

    published_properties = PublishedProperties({
        "transformation": Property(default_transformation, lambda self: self.transformation, set_transformation)
    })

    #
    # Dialog fields (see action EditProperties)
    #

    dialog_fields = set([
        DialogFieldInfo("Translation", (3, 0), fields.composed.Translation(
            label_text="Translation with vector t",
            attribute_name="transformation",
            invalid_message="Make sure that the fields that describe the translation, are correct.",
        )),
        DialogFieldInfo("Rotation", (4, 0), fields.composed.Rotation(
            label_text="Rotation around axis n",
            attribute_name="transformation",
            invalid_message="Make sure that the fields that describe the rotation, are correct.",
        )),
        DialogFieldInfo("Rotation", (4, 1), fields.read.Handedness()),
    ])

    #
    # OpenGL
    #

    def initialize_gl(self):
        self.transformation_list = glGenLists(1)
        ##print "Created transformation list (%i): %s" % (self.transformation_list, self.get_name())
        self.transformation_list_valid = True
        GLMixin.initialize_gl(self)

    def cleanup_gl(self):
        GLMixin.cleanup_gl(self)
        ##print "Deleting transformation list (%i): %s" % (self.transformation_list, self.get_name())
        glDeleteLists(self.transformation_list, 1)
        del self.transformation_list
        del self.transformation_list_valid

    #
    # Invalidation
    #

    def invalidate_transformation_list(self):
        if self.gl_active > 0 and self.transformation_list_valid:
            self.transformation_list_valid = False
            context.application.main.drawing_area.queue_draw()
            context.application.main.drawing_area.scene.add_revalidation(self.revalidate_transformation_list)
            self.emit("on-transformation-list-invalidated")
            ##print "EMIT %s: on-transformation-list-invalidated" % self.get_name()
            if isinstance(self.parent, GLMixin):
                self.parent.invalidate_boundingbox_list()

    def invalidate_all_lists(self):
        self.invalidate_transformation_list()
        GLMixin.invalidate_all_lists(self)

    #
    # Draw
    #

    def write_pov(self, indenter):
        GLMixin.write_pov(self, indenter)
        if self.Transformation == Translation:
            indenter.write_line("translate <%f, %f, %f>" % tuple(self.transformation.translation_vector))
        elif self.Transformation == Rotation:
            indenter.write_line("matrix <%f, %f, %f, %f, %f, %f, %f, %f, %f, 0.0, 0.0, 0.0>" % tuple(numpy.ravel(numpy.transpose(self.transformation.rotation_matrix))))
        else:
            indenter.write_line("matrix <%f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f>" % (tuple(numpy.ravel(numpy.transpose(self.transformation.rotation_matrix))) + tuple(self.transformation.translation_vector)))

    #
    # Revalidation
    #

    def revalidate_transformation_list(self):
        if self.gl_active > 0:
            ##print "Compiling transformation list (%i): %s" % (self.transformation_list,  self.get_name())
            glNewList(self.transformation_list, GL_COMPILE)
            glPushMatrix()
            self.transformation.gl_apply()
            glEndList()
            self.transformation_list_valid = True

    def revalidate_total_list(self):
        if self.gl_active > 0:
            ##print "Compiling total list (%i): %s" % (self.total_list, self.get_name())
            glNewList(self.total_list, GL_COMPILE)
            if self.visible:
                glPushName(self.draw_list)
                glCallList(self.transformation_list)
                if self.selected: glCallList(self.boundingbox_list)
                glCallList(self.draw_list)
                glPopMatrix()
                glPopName()
            glEndList()
            self.total_list_valid = True

    #
    # Frame
    #

    def get_bounding_box_in_parent_frame(self):
        return self.bounding_box.transformed(self.transformation)

    def get_absolute_frame(self):
        if not isinstance(self.parent, GLMixin):
            return copy.deepcopy(self.transformation)
        else:
            temp = self.get_absolute_parentframe()
            temp.apply_before(self.transformation)
            return temp

    def get_frame_up_to(self, upper_parent):
        if (upper_parent == self):
            return Complete()
        elif (self.parent == upper_parent):
            return copy.deepcopy(self.transformation)
        else:
            temp = self.get_parentframe_up_to(upper_parent)
            temp.apply_before(self.transformation)
            return temp

gobject.signal_new("on-transformation-list-invalidated", GLTransformationMixin, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())


