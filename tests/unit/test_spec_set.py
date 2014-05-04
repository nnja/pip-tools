import unittest

import six

from piptools.datastructures import ConflictError, Spec, SpecSet


class UnitTestPython3CompatMixin(object):
    def assertCountEqual(self, first, second, msg=None):
        if six.PY2:
            return self.assertItemsEqual(first, second, msg)
        return self.assertCountEqual(first, second, msg)


class TestSpecSet(unittest.TestCase, UnitTestPython3CompatMixin):
    def test_adding_spec(self):
        """Adding a spec to a set."""
        specset = SpecSet()

        specset.add_spec('foo')
        specset.add_spec('foo')

        self.assertCountEqual(list(specset),
                              [Spec.from_line('foo')])

        # If we now add a 'foo' spec from a specific source, they're not
        # considered equal
        spec = Spec.from_line('foo', source='bar==1.2.4')
        specset.add_spec(spec)

        self.assertCountEqual(list(specset),
                              [spec, Spec.from_line('foo')])

    def test_adding_multiple_specs(self):
        """Adding multiple specs to a set."""
        specset = SpecSet()

        specset.add_spec('Django>=1.3')
        assert 'Django>=1.3' in list(map(str, specset))

        specset.add_spec('django-pipeline')
        self.assertCountEqual(['Django>=1.3', 'django-pipeline'], list(map(str, specset)))

        specset.add_spec('Django<1.4')
        self.assertCountEqual(['Django>=1.3', 'django-pipeline', 'Django<1.4'], list(map(str, specset)))

    def test_explode(self):
        """Exploding a spec list into specs of max one predicate."""
        specset = SpecSet()

        specset.add_spec('Django>=1.3,<1.4')
        specset.add_spec('Django>=1.3.2,<1.5')

        self.assertCountEqual(
            ['Django>=1.3', 'Django>=1.3.2', 'Django<1.4', 'Django<1.5'],
            list(map(str, specset.explode('Django'))))

    def test_normalizing_combines(self):
        """Normalizing combines predicates to a single Spec."""
        specset = SpecSet()

        specset.add_spec('Django>=1.3')
        specset.add_spec('Django<1.4')
        specset.add_spec('Django>=1.3.2')
        specset.add_spec('Django<1.3.99')

        normalized = str(specset.normalize())
        assert 'django<1.3.99,>=1.3.2' in normalized

        specset.add_spec('Django<=1.3.2')
        normalized = specset.normalize()

        assert 'django==1.3.2' in list(map(str, normalized))

    def test_normalizing_drops_obsoletes(self):
        """Normalizing combines predicates to a single Spec."""
        specset = SpecSet()

        specset.add_spec('Django')
        specset.add_spec('Django<1.4')

        normalized = specset.normalize()
        assert 'django<1.4' in list(map(str, normalized))
        assert 'django' not in list(map(str, normalized))

        specset = SpecSet()
        specset.add_spec('Django>=1.4.1')
        specset.add_spec('Django!=1.3.3')

        normalized = specset.normalize()
        assert 'django>=1.4.1' in list(map(str, normalized))
        assert 'django!=1.3.3' not in list(map(str, normalized))

    def test_normalizing_multiple_notequal_ops(self):
        """Normalizing multiple not-equal ops."""
        specset = SpecSet()
        specset.add_spec('Django!=1.3')
        specset.add_spec('Django!=1.4')

        normalized = specset.normalize()
        assert 'django!=1.3,!=1.4' in list(map(str, normalized))

    def test_normalizing_unequal_op(self):
        """Normalizing inequality and not-equal ops."""
        specset = SpecSet()
        specset.add_spec('Django>=1.4.1')
        specset.add_spec('Django!=1.4.1')

        normalized = specset.normalize()
        assert 'django>1.4.1' in list(map(str, normalized))

        specset = SpecSet()
        specset.add_spec('Django<=1.4.1')
        specset.add_spec('Django!=1.4.1')

        normalized = specset.normalize()
        assert 'django<1.4.1' in list(map(str, normalized))

        specset = SpecSet()
        specset.add_spec('Django>=1.4.1')
        specset.add_spec('Django!=1.4.2')

        normalized = str(specset.normalize())
        assert 'django!=1.4.2,>=1.4.1' in normalized

        specset = SpecSet()
        specset.add_spec('Django<=1.4.1')
        specset.add_spec('Django>=1.4.1')
        specset.add_spec('Django!=1.4.1')

        with self.assertRaises(ConflictError):
            specset.normalize()

    def test_normalizing_conflicts(self):
        """Normalizing can lead to conflicts."""
        specset = SpecSet()
        specset.add_spec('Django==1.4.1')
        specset.add_spec('Django!=1.4.1')

        with self.assertRaises(ConflictError):
            specset.normalize()

    def test_normalizing_keeps_source_info(self):
        """Normalizing keeps source information for specs."""
        specset = SpecSet()

        specset.add_spec(Spec.from_line('Django', source='foo'))

        normalized = specset.normalize()
        assert 'foo' in [spec.source for spec in normalized]

        specset.add_spec(Spec.from_line('Django<1.4', source='bar'))
        specset.add_spec(Spec.from_line('Django<1.4', source='qux'))
        specset.add_spec(Spec.from_line('Django<1.4', source='mutt'))

        normalized = specset.normalize()
        assert 'foo' not in [spec.source for spec in normalized]
        assert 'bar and mutt and qux' in [spec.source for spec in normalized]
