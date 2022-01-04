from __future__ import annotations
from functools import wraps
import numpy as np
from ..misc import FreeWidget

class PyVistaCanvas(FreeWidget):
    def __init__(self, **kwargs):
        from pyvistaqt import QtInteractor
        super().__init__(**kwargs)
        widget = QtInteractor(parent=self.native)
        self.set_widget(widget)
        self.central_widget: QtInteractor
    
    def add_mesh(self, mesh, **kwargs):
        self.central_widget.add_mesh(mesh, **kwargs)
    
    def add_points(self, points: np.ndarray, **kwargs):
        self.central_widget.add_points(points, **kwargs)

shared_doc = """

        Parameters
        ----------
        mesh : pyvista.DataSet or pyvista.MultiBlock
            Any PyVista or VTK mesh is supported. Also, any dataset
            that :func:`pyvista.wrap` can handle including NumPy
            arrays of XYZ points.

        color : str or 3 item list, optional, defaults to white
            Use to make the entire mesh have a single solid color.
            Either a string, RGB list, or hex color string.  For example:
            ``color='white'``, ``color='w'``, ``color=[1, 1, 1]``, or
            ``color='#FFFFFF'``. Color will be overridden if scalars are
            specified.

        style : str, optional
            Visualization style of the mesh.  One of the following:
            ``style='surface'``, ``style='wireframe'``, ``style='points'``.
            Defaults to ``'surface'``. Note that ``'wireframe'`` only shows a
            wireframe of the outer geometry.

        scalars : str or numpy.ndarray, optional
            Scalars used to "color" the mesh.  Accepts a string name
            of an array that is present on the mesh or an array equal
            to the number of cells or the number of points in the
            mesh.  Array should be sized as a single vector. If both
            ``color`` and ``scalars`` are ``None``, then the active
            scalars are used.

        clim : 2 item list, optional
            Color bar range for scalars.  Defaults to minimum and
            maximum of scalars array.  Example: ``[-1, 2]``. ``rng``
            is also an accepted alias for this.

        show_edges : bool, optional
            Shows the edges of a mesh.  Does not apply to a wireframe
            representation.

        edge_color : str or 3 item list, optional, defaults to black
            The solid color to give the edges when ``show_edges=True``.
            Either a string, RGB list, or hex color string.

        point_size : float, optional
            Point size of any nodes in the dataset plotted. Also
            applicable when style='points'. Default ``5.0``.

        line_width : float, optional
            Thickness of lines.  Only valid for wireframe and surface
            representations.  Default None.

        opacity : float, str, array-like
            Opacity of the mesh. If a single float value is given, it
            will be the global opacity of the mesh and uniformly
            applied everywhere - should be between 0 and 1. A string
            can also be specified to map the scalars range to a
            predefined opacity transfer function (options include:
            'linear', 'linear_r', 'geom', 'geom_r').  A string could
            also be used to map a scalars array from the mesh to the
            opacity (must have same number of elements as the
            ``scalars`` argument). Or you can pass a custom made
            transfer function that is an array either ``n_colors`` in
            length or shorter.

        flip_scalars : bool, optional
            Flip direction of cmap. Most colormaps allow ``*_r``
            suffix to do this as well.

        lighting : bool, optional
            Enable or disable view direction lighting. Default ``False``.

        n_colors : int, optional
            Number of colors to use when displaying scalars. Defaults to 256.
            The scalar bar will also have this many colors.

        interpolate_before_map : bool, optional
            Enabling makes for a smoother scalars display.  Default is
            ``True``.  When ``False``, OpenGL will interpolate the
            mapped colors which can result is showing colors that are
            not present in the color map.

        cmap : str, list, optional
            Name of the Matplotlib colormap to use when mapping the
            ``scalars``.  See available Matplotlib colormaps.  Only
            applicable for when displaying ``scalars``. Requires
            Matplotlib to be installed.  ``colormap`` is also an
            accepted alias for this. If ``colorcet`` or ``cmocean``
            are installed, their colormaps can be specified by name.

            You can also specify a list of colors to override an
            existing colormap with a custom one.  For example, to
            create a three color colormap you might specify
            ``['green', 'red', 'blue']``.

        label : str, optional
            String label to use when adding a legend to the scene with
            :func:`pyvista.BasePlotter.add_legend`.

        reset_camera : bool, optional
            Reset the camera after adding this mesh to the scene.

        scalar_bar_args : dict, optional
            Dictionary of keyword arguments to pass when adding the
            scalar bar to the scene. For options, see
            :func:`pyvista.BasePlotter.add_scalar_bar`.

        show_scalar_bar : bool
            If ``False``, a scalar bar will not be added to the
            scene. Defaults to ``True``.

        multi_colors : bool, optional
            If a ``MultiBlock`` dataset is given this will color each
            block by a solid color using matplotlib's color cycler.

        name : str, optional
            The name for the added mesh/actor so that it can be easily
            updated.  If an actor of this name already exists in the
            rendering window, it will be replaced by the new actor.

        texture : vtk.vtkTexture or np.ndarray or bool, optional
            A texture to apply if the input mesh has texture
            coordinates.  This will not work with MultiBlock
            datasets. If set to ``True``, the first available texture
            on the object will be used. If a string name is given, it
            will pull a texture with that name associated to the input
            mesh.

        render_points_as_spheres : bool, optional
            Render points as spheres rather than dots.

        render_lines_as_tubes : bool, optional
            Show lines as thick tubes rather than flat lines.  Control
            the width with ``line_width``.

        smooth_shading : bool, optional
            Enable smooth shading when ``True`` using either the 
            Gouraud or Phong shading algorithm.  When ``False``, use
            flat shading.
            Automatically enabled when ``pbr=True``.

        ambient : float, optional
            When lighting is enabled, this is the amount of light in
            the range of 0 to 1 (default 0.0) that reaches the actor
            when not directed at the light source emitted from the
            viewer.

        diffuse : float, optional
            The diffuse lighting coefficient. Default 1.0.

        specular : float, optional
            The specular lighting coefficient. Default 0.0.

        specular_power : float, optional
            The specular power. Between 0.0 and 128.0.

        nan_color : str or 3 item list, optional, defaults to gray
            The color to use for all ``NaN`` values in the plotted
            scalar array.

        nan_opacity : float, optional
            Opacity of ``NaN`` values.  Should be between 0 and 1.
            Default 1.0.

        culling : str, optional
            Does not render faces that are culled. Options are
            ``'front'`` or ``'back'``. This can be helpful for dense
            surface meshes, especially when edges are visible, but can
            cause flat meshes to be partially displayed.  Defaults to
            ``False``.

        rgb : bool, optional
            If an 2 dimensional array is passed as the scalars, plot
            those values as RGB(A) colors. ``rgba`` is also an
            accepted alias for this.  Opacity (the A) is optional.  If
            a scalars array ending with ``"_rgba"`` is passed, the default
            becomes ``True``.  This can be overridden by setting this
            parameter to ``False``.

        categories : bool, optional
            If set to ``True``, then the number of unique values in
            the scalar array will be used as the ``n_colors``
            argument.

        silhouette : dict, bool, optional
            If set to ``True``, plot a silhouette highlight for the
            mesh. This feature is only available for a triangulated
            ``PolyData``.  As a ``dict``, it contains the properties
            of the silhouette to display:

                * ``color``: ``str`` or 3-item ``list``, color of the silhouette
                * ``line_width``: ``float``, edge width
                * ``opacity``: ``float`` between 0 and 1, edge transparency
                * ``feature_angle``: If a ``float``, display sharp edges
                  exceeding that angle in degrees.
                * ``decimate``: ``float`` between 0 and 1, level of decimation

        use_transparency : bool, optional
            Invert the opacity mappings and make the values correspond
            to transparency.

        below_color : str or 3 item list, optional
            Solid color for values below the scalars range
            (``clim``). This will automatically set the scalar bar
            ``below_label`` to ``'Below'``.

        above_color : str or 3 item list, optional
            Solid color for values below the scalars range
            (``clim``). This will automatically set the scalar bar
            ``above_label`` to ``'Above'``.

        annotations : dict, optional
            Pass a dictionary of annotations. Keys are the float
            values in the scalars range to annotate on the scalar bar
            and the values are the the string annotations.

        pickable : bool, optional
            Set whether this actor is pickable.

        preference : str, optional
            When ``mesh.n_points == mesh.n_cells`` and setting
            scalars, this parameter sets how the scalars will be
            mapped to the mesh.  Default ``'points'``, causes the
            scalars will be associated with the mesh points.  Can be
            either ``'points'`` or ``'cells'``.

        log_scale : bool, optional
            Use log scale when mapping data to colors. Scalars less
            than zero are mapped to the smallest representable
            positive float. Default: ``True``.

        pbr : bool, optional
            Enable physics based rendering (PBR) if the mesh is
            ``PolyData``.  Use the ``color`` argument to set the base
            color. This is only available in VTK>=9.

        metallic : float, optional
            Usually this value is either 0 or 1 for a real material
            but any value in between is valid. This parameter is only
            used by PBR interpolation. Default value is 0.0.

        roughness : float, optional
            This value has to be between 0 (glossy) and 1 (rough). A
            glossy material has reflections and a high specular
            part. This parameter is only used by PBR
            interpolation. Default value is 0.5.

        render : bool, optional
            Force a render when ``True``.  Default ``True``.

        component :  int, optional
            Set component of vector valued scalars to plot.  Must be
            nonnegative, if supplied. If ``None``, the magnitude of
            the vector is plotted.
        """