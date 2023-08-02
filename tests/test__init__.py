import factory  # type: ignore
import gcspathlib
import pytest
from pathlib import PurePosixPath


class PureGCSPathFactory(factory.Factory):
    class Meta:
        model = gcspathlib.PureGCSPath

    class Params:
        bucket = factory.Faker('lexify', text='bucket-??????')
        depth = 1
        extension = factory.Faker('file_extension')
        obj = factory.Faker(
            'file_path',
            extension=factory.SelfAttribute('..extension'),
            absolute=False,
        )

    path = factory.LazyAttribute(
        lambda stub: f'{gcspathlib.URI_PREFIX}{stub.bucket}/{stub.obj}'
    )

    @classmethod
    def _create(cls, model_class, *, path):
        return model_class(path)


class Test_PureGCSPath:
    def test__init_empty(self):
        path = gcspathlib.PureGCSPath()
        assert path.drive == ''
        assert path.parts == tuple()
        assert path.name == ''
        assert path.suffix == ''
        assert path.stem == ''
        assert path.bucket == ''
        assert path.obj == ''
        assert path.is_absolute() is False
        assert bool(path) is False
        assert str(path) == '.'  # FIXME: undesirable default behavior

    def test__init_absolute(self):
        uri = 'gs://bucket/dir1/dir2/file.txt'
        path = gcspathlib.PureGCSPath(uri)
        assert path.drive == 'gs://bucket'
        assert path.parts == ('gs://bucket/', 'dir1', 'dir2', 'file.txt')
        assert path.name == 'file.txt'
        assert path.suffix == '.txt'
        assert path.stem == 'file'
        assert path.bucket == 'bucket'
        assert path.obj == 'dir1/dir2/file.txt'
        assert path.is_absolute() is True
        assert bool(path) is True
        assert path.as_uri() == uri
        assert str(path) == uri

    def test__init_bucketless(self):
        obj = 'dir1/dir2/file.txt'
        path = gcspathlib.PureGCSPath(obj)
        assert path.drive == ''
        assert path.parts == ('dir1', 'dir2', 'file.txt')
        assert path.name == 'file.txt'
        assert path.suffix == '.txt'
        assert path.stem == 'file'
        assert path.bucket == ''
        assert path.obj == obj
        assert path.is_absolute() is False
        assert bool(path) is False
        assert str(path) == obj
        with pytest.raises(ValueError) as excinfo:
            path.as_uri()
        assert str(excinfo.value) == 'relative path can\'t be expressed as a file URI'

    def test__init_bucket_only(self):
        uri = 'gs://bucket'
        path = gcspathlib.PureGCSPath(uri)
        assert path.drive == 'gs://bucket'
        assert path.parts == ('gs://bucket/',)
        assert path.name == ''
        assert path.suffix == ''
        assert path.stem == ''
        assert path.bucket == 'bucket'
        assert path.obj == ''
        assert path.is_absolute() is False
        assert bool(path) is False
        assert str(path) == 'gs://bucket/'
        with pytest.raises(ValueError) as excinfo:
            path.as_uri()
        assert str(excinfo.value) == 'relative path can\'t be expressed as a file URI'

    def test__init_from_parts(self):  # TODO: combine with other tests
        path = gcspathlib.PureGCSPath('/', 'dir', 'file')
        assert path.parts == ('dir', 'file')

        path = gcspathlib.PureGCSPath('gs://bucket', 'dir', 'file')
        assert path.parts == ('gs://bucket/', 'dir', 'file')

        path = gcspathlib.PureGCSPath('gs://bucket/', 'dir', 'file')
        assert path.parts == ('gs://bucket/', 'dir', 'file')

        path = gcspathlib.PureGCSPath('/', 'file', 'gs://bucket/file')
        assert path.parts == ('gs://bucket/', 'file')

    def test__init_with_extra_slashes(self):
        path = gcspathlib.PureGCSPath('gs://bucket//dir//file')
        assert path.parts == ('gs://bucket/', 'dir', 'file')

        path = gcspathlib.PureGCSPath('/dir//file')
        assert path.parts == ('dir', 'file')

        path = gcspathlib.PureGCSPath('//file')
        assert path.parts == ('file',)

    def test__init_with_invalid_uri(self):
        with pytest.raises(ValueError) as excinfo:
            gcspathlib.PureGCSPath('gs://')
        assert str(excinfo.value) == 'Invalid bucket name in URI: gs://'

        with pytest.raises(ValueError) as excinfo:
            gcspathlib.PureGCSPath('gs:///')
        assert str(excinfo.value) == 'Invalid bucket name in URI: gs:///'

        with pytest.raises(ValueError) as excinfo:
            gcspathlib.PureGCSPath('gs:///dir')
        assert str(excinfo.value) == 'Invalid bucket name in URI: gs:///dir'

    def test_with_bucket(self):
        path = gcspathlib.PureGCSPath().with_bucket('bucket1')
        assert path.bucket == 'bucket1'
        assert path.obj == ''
        assert path.parts == ('gs://bucket1/',)

        path = gcspathlib.PureGCSPath('dir/file.txt').with_bucket('bucket1')
        assert path.bucket == 'bucket1'
        assert path.obj == 'dir/file.txt'
        assert path.parts == ('gs://bucket1/', 'dir', 'file.txt')

        path = path.with_bucket('bucket2')
        assert path.bucket == 'bucket2'
        assert path.obj == 'dir/file.txt'
        assert path.parts == ('gs://bucket2/', 'dir', 'file.txt')

    def test_without_bucket(self):
        path = gcspathlib.PureGCSPath('gs://bucket1/dir/file.txt').without_bucket()
        assert path.drive == ''
        assert path.bucket == ''
        assert path.obj == 'dir/file.txt'
        assert path.parts == ('dir', 'file.txt')

        path = path.without_bucket()
        assert path.drive == ''
        assert path.bucket == ''
        assert path.obj == 'dir/file.txt'
        assert path.parts == ('dir', 'file.txt')

    def test_with_obj(self):
        path = gcspathlib.PureGCSPath().with_obj('dir/file.txt')
        assert path.bucket == ''
        assert path.obj == 'dir/file.txt'
        assert path.parts == ('dir', 'file.txt')

        path = gcspathlib.PureGCSPath('file.txt').with_obj('dir/file2.txt')
        assert path.bucket == ''
        assert path.obj == 'dir/file2.txt'
        assert path.parts == ('dir', 'file2.txt')

        path = gcspathlib.PureGCSPath('gs://bucket/file.txt').with_obj('dir/file2.txt')
        assert path.bucket == 'bucket'
        assert path.obj == 'dir/file2.txt'
        assert path.parts == ('gs://bucket/', 'dir', 'file2.txt')

        path = gcspathlib.PureGCSPath('gs://bucket').with_obj('dir', 'file.txt')
        assert path.bucket == 'bucket'
        assert path.obj == 'dir/file.txt'
        assert path.parts == ('gs://bucket/', 'dir', 'file.txt')

    def test_join(self):
        path = gcspathlib.PureGCSPath('gs://bucket/dir1')
        joined_path = path / 'dir2' / 'file.txt'
        assert isinstance(joined_path, gcspathlib.PureGCSPath)
        assert str(joined_path) == 'gs://bucket/dir1/dir2/file.txt'

        other_path = PurePosixPath('qux/quz')
        combined_path = path / other_path
        assert str(combined_path) == 'gs://bucket/dir1/qux/quz'

    def test__equality(self):
        path = PureGCSPathFactory()
        assert path == gcspathlib.PureGCSPath(str(path))
        assert path != PureGCSPathFactory()
        assert path != gcspathlib.PureGCSPath(path.obj)

    def test__hashability(self):
        path1 = PureGCSPathFactory()
        path2 = PureGCSPathFactory()
        my_dict = {path1: path1, path2: path2}
        assert my_dict[path1] is path1
        assert my_dict[gcspathlib.PureGCSPath(path1)] is path1
        assert my_dict[path2] is path2

    def test_parent__absolute(self):
        path = gcspathlib.PureGCSPath('gs://bucket/dir1/file.txt')
        assert path.parent == gcspathlib.PureGCSPath('gs://bucket/dir1')
        assert path.parent.parent == gcspathlib.PureGCSPath('gs://bucket/')
        assert path.parent.parent.parent == gcspathlib.PureGCSPath('gs://bucket/')

        path = gcspathlib.PureGCSPath('gs://bucket/dir1/file.txt')

    def test_relative_to(self):
        path = gcspathlib.PureGCSPath('gs://bucket/dir1/dir2/file.txt')
        assert path.relative_to(
            gcspathlib.PureGCSPath('gs://bucket/dir1')
        ) == gcspathlib.PureGCSPath('dir2/file.txt')

    def test__immutability(faker):
        path = PureGCSPathFactory()
        with pytest.raises(AttributeError):
            path.bucket = faker.lexify()
        with pytest.raises(AttributeError):
            path.drive = faker.lexify()
        with pytest.raises(AttributeError):
            path.name = faker.lexify()
        with pytest.raises(AttributeError):
            path.suffix = faker.lexify()
        with pytest.raises(AttributeError):
            path.obj = faker.lexify()
