import pathlib
import urllib.parse
from typing import ClassVar
from typing import Self

URI_PREFIX = 'gs://'


class _GCSFlavour(
    pathlib._PosixFlavour,  # type: ignore[misc,name-defined]  # pylint: disable=protected-access
):
    """Implementation of the core :mod:`pathlib` functionality for Cloud Storage paths.

    :class:`pathlib._Flavour` is an internal implementation detail of :mod:`pathlib`,
    but extending it in this manner along with a :class:`PureGCSPath` implementation
    enables use of the standard :class:`pathlib.PurePath` functionality without
    reinventing the wheel.

    Warning:
        This could certainly break across Python versions if :mod:`pathlib` is ever
        refactored, but that's a price worth paying.
    """

    is_supported: ClassVar[bool] = False  # only "Pure" implementation is allowed

    def splitroot(
        self,
        part: str,
        sep: str = '/',
    ) -> tuple[str, str, str]:
        drive: str
        root: str
        rel: str
        if part and part.startswith(URI_PREFIX):
            bucket, _, rel = part.removeprefix(URI_PREFIX).partition(sep)
            if not bucket:
                raise ValueError(f'Invalid bucket name in URI: {part}')
            drive = URI_PREFIX + bucket
            root = sep
            # part = sep + root + rel
            rel = sep + rel  # TBD
        else:
            drive = ''
            root = ''
            rel = part
        return drive, root, rel

    def make_uri(
        self,
        path: pathlib.PurePath,
    ) -> str:
        assert isinstance(path, PureGCSPath)
        assert path.is_absolute()
        return URI_PREFIX + urllib.parse.quote(f'{path.bucket}{self.sep}{path.obj}')


_gcs_flavour = _GCSFlavour()


class PureGCSPath(pathlib.PurePath):
    """A :class:`pathlib.PurePath` subclass that represents Cloud Storage paths.

    The purpose of this class is to provide a :class:`pathlib.PurePath` compatible
    interface for manipulating Cloud Storage bucket and object names as paths.

    Just like :class:`pathlib.PurePath`, this is a "pure" path because it performs no
    I/O operations on its own. The main goal is to handle the path manipulation part,
    while actual I/O with Google Cloud Storage is considered outside the scope of this
    class, keeping the library lightweight.

    Note:
        The compatibility with :class:`pathlib.PurePath` means it can be used
        interchangeably with :class:`pathlib.PurePosixPath` or
        :class:`pathlib.PureWindowsPath`, making it versatile for local or cloud storage
        applications.
    """

    _flavour = _gcs_flavour
    __slots__ = ()

    @property
    def _bucket_parts(self) -> tuple[str, ...]:
        return (self.parts[0],) if self.drive else tuple()

    @property
    def _obj_parts(self) -> tuple[str, ...]:
        return self.parts[1:] if self.drive else self.parts

    @property
    def bucket(self) -> str:
        """The Cloud Storage bucket that this path points to.

        If the path has no bucket (i.e. a relative path), an empty string is returned.
        """
        return self.drive.removeprefix(URI_PREFIX).removesuffix(self._flavour.sep)

    def with_bucket(
        self,
        new_bucket: str,
    ) -> Self:
        """Returns a new :class:`PureGCSPath` object with the specified bucket."""
        new_drive = f'{URI_PREFIX}{new_bucket}{self._flavour.sep}'
        return type(self)(new_drive, *self._obj_parts)

    def without_bucket(self) -> Self:
        return type(self)(*self._obj_parts)

    @property
    def obj(self) -> str:
        """The Cloud Storage object name of the path, if available.

        If the path is bucket-only, an empty string is returned.
        """
        sep: str = self._flavour.sep
        return sep.join(self._obj_parts)

    def with_obj(
        self,
        *obj_parts: str,
    ) -> Self:
        """Constructs a new path with the same bucket but different object name.

        The object name can be expressed in parts if desired, like calling the normal
        constructor with multiple positional arguments.

        Todo:
            Possibly enforce lack of ``gs://`` in ``obj_parts`` because otherwise the
            caller can inadvertently switch to a different bucket without realizing it,
            which could be a security vulnerability in certain cases.

            It's technically possible for a GCS object name to include ``gs://``, so it
            could theoretically be supported as a relative path, but it's a can of worms
            and requires careful consideration; might be better to just reject it.
            However, the same issue applies when joining paths - e.g. via the ``/``
            operator, which allows changing to a different bucket - just like in other
            :class:`pathlib.PurePath` implementations.

            One way or another though, there needs to be a way for a caller to reliably
            build GCS URIs without having to manually check for such oddities.
        """
        return type(self)(*self._bucket_parts, *obj_parts)

    def without_obj(
        self,
    ) -> Self:
        return type(self)(*self._bucket_parts)


__all__ = [
    'PureGCSPath',
    'URI_PREFIX',
]
