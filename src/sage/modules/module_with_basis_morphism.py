r"""
Module morphisms from a module with basis

This module contains a hierarchy of classes for modules with bases:

- :class:`ModuleMorphism`
- :class:`ModuleMorphismByLinearity`
- :class:`ModuleMorphismFromMatrix`
- :class:`ModuleMorphismFromFunction`
- :class:`TriangularModuleMorphism`
- :class:`TriangularModuleMorphismByLinearity`
- :class:`TriangularModuleMorphismFromFunction`

Those are internal classes; it is strongly recommended *not* to use
them directly, and instead to always construct morphisms through the
:meth:`ModulesWithBasis.ParentMethods.module_morphism` method of
domain, or through the homset; see the former for an overview
description of the arguments.

EXAMPLES::

    sage: X = CombinatorialFreeModule(QQ, [1,2,3]);   x = X.basis()
    sage: Y = CombinatorialFreeModule(QQ, [1,2,3,4]); y = Y.basis()
    sage: on_basis = lambda i: Y.monomial(i) + 2*Y.monomial(i+1)

    sage: phi1 = X.module_morphism(on_basis, codomain = Y)
    sage: phi1(x[1])
    B[1] + 2*B[2]

    sage: H = Hom(X,Y)
    sage: phi2 = H(on_basis=on_basis)
    sage: phi1 == phi2
    True

No backward compatibility is guaranteed for this one::

    sage: from sage.modules.module_with_basis_morphism import ModuleMorphismByLinearity
    sage: phi3 = ModuleMorphismByLinearity(X, on_basis, codomain=Y)
    sage: phi3 == phi1
    True


.. WARNING::

    The hierarchy of classes implemented in this module is one of the
    first non trivial hierarchy of classes for morphisms. It is
    hitting a couple scaling issues:

    - There are many independent properties from which module
      morphisms can get code (being defined by linearity, from a
      matrix, or a function; being triangular, being diagonal,
      ...). How to mitigate the class hierarchy growth?

      This will become even more stringent as more properties are
      added (e.g. being defined from generators for an algebra
      morphism, ...)

      Categories, whose primary purpose is to provide infrastructure
      for handling such large hierarchy of classes, can't help at this
      point: there is no category whose morphisms are triangular
      morphisms, and it's not clear such a category would be sensible.

    - How to properly handle ``__init__`` method calls and
      multiple inheritance.

    - Who should be in charge of setting the default category: the
      classes themselves, or
      :meth:`ModulesWithBasis.ParentMethods.module_morphism`.

    Because of this the hierarchy of classes, and their specific APIs,
    is likely to be refactored as better infrastructure and best
    practices emerge.

AUTHORS:

- Nicolas M. Thiery (2008-2015):
- Jason Bandlow and Florent Hivert (2010): Triangular Morphisms
- Christian Stump (2010): :trac:`9648` module_morphism's to a wider class
  of codomains

Before :trac:`8678`, this hierarchy of classes used to be in
sage.categories.modules_with_basis, which see for the complete log.
"""
#*****************************************************************************
#  Copyright (C) 2015 Nicolas M. Thiery <nthiery at users.sf.net>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#                  http://www.gnu.org/licenses/
#******************************************************************************

from sage.categories.fields import Fields
from sage.categories.modules import Modules
from sage.misc.misc import attrcall
from sage.misc.cachefunc import cached_method
from sage.misc.superseded import deprecated_function_alias
from sage.categories.commutative_additive_semigroups import CommutativeAdditiveSemigroups
from sage.categories.homset import Hom
from sage.categories.modules_with_basis import ModulesWithBasis
from sage.categories.morphism import SetMorphism, Morphism
from sage.categories.sets_cat import Sets
from sage.categories.sets_with_partial_maps import SetsWithPartialMaps
from sage.structure.element import parent

class ModuleMorphism(Morphism):
    """
    The top abstract base class for module with basis morphisms.

    INPUT:

    - ``domain`` -- a parent in ``ModulesWithBasis(...)``
    - ``codomain`` -- a parent in ``Modules(...)``;
    - ``category`` -- a category or ``None`` (default: `None``)

    Construct a module morphism from ``domain`` to ``codomain`` in the
    category ``category``. By default, the category is the first of
    ``Modules(R).WithBasis().FiniteDimensional()``,
    ``Modules(R).WithBasis()`` ``Modules(R)``,
    ``CommutativeAdditiveMonoids()`` that contains both the domain and
    the codomain.


    The role of this class is minimal; it provides an :meth:`__init__`
    method which::

    - handles the choice of the default category
    - handles the proper inheritance from categories by updating the
      class of ``self`` upon construction.


    """
    def __init__(self, domain, codomain=None, category=None, affine=False):
        """
        TESTS::

            sage: X = CombinatorialFreeModule(ZZ, [-2, -1, 1, 2])
            sage: Y = CombinatorialFreeModule(ZZ, [1, 2])
            sage: from sage.modules.module_with_basis_morphism import ModuleMorphismByLinearity
            sage: phi = ModuleMorphismByLinearity(X, on_basis=Y.monomial * abs)
            sage: TestSuite(phi).run()
        """
        if category is None:
            if not domain in ModulesWithBasis:
                raise ValueError("domain(=%s) should be a module with basis"%(codomain))
            base_ring = domain.base_ring()

            if not hasattr( codomain, 'base_ring' ):
                raise ValueError("codomain(=%s) needs to have a base_ring attribute"%(codomain))
            # codomain should be a module over base_ring
            # The natural test would be ``codomains in Modules(base_ring)``
            # But this is not properly implemented yet:
            #     sage: CC in Modules(QQ)
            #     False
            #     sage: QQ in Modules(QQ)
            #     False
            #     sage: CC[x] in Modules(QQ)
            #     False
            # The test below is a bit more restrictive
            if (not codomain.base_ring().has_coerce_map_from(base_ring)) \
               and (not codomain.has_coerce_map_from(base_ring)):
                raise ValueError("codomain(=%s) should be a module over the base ring of the domain(=%s)"%(codomain, domain))

            if affine:
                # We don't yet have a category whose morphisms are affine morphisms
                category = Sets()
            else:
                C = Modules(base_ring)
                for C in [C.WithBasis().FiniteDimensional(),
                          C.WithBasis(),
                          C,
                          # QQ is not in Modules(QQ)!
                          CommutativeAdditiveSemigroups()]:
                    if codomain in C and domain in C:
                        category = C
                        break
                if category is None:
                    raise ValueError("codomain=(%s) should at least be a commutative additive semigroup")

        H = Hom(domain, codomain, category=category)
        Morphism.__init__(self, H)

        # If needed, this creates the element class from the concrete
        # class (ModuleMorphismByLinearity, DiagonalModuleMorphism,
        # ...) and the abstract classes from the categories.
        #
        # The category infrastructure handles this automatically for
        # parents with a single element class. But for now we still
        # need to do it by hand here, since H may have many different
        # element classes::
        if not issubclass(self.__class__, H._abstract_element_class):
            self.__class__ = H.__make_element_class__(self.__class__)

class ModuleMorphismFromFunction(ModuleMorphism, SetMorphism):
    """
    A class for module morphisms implemented by a plain function

    INPUT:

    - ``domain``, ``codomain``, ``category`` --
      As for :class:`ModuleMorphismFromFunction`, which see.

    - ``matrix`` -- a matrix with base ring `R` and dimensions
      matching that of the domain and codomain respectively

    - ``side`` -- "left" or "right" (default: "left")

        If ``side`` is "left", this morphism is considered as
        acting on the left; i.e. each column of the matrix
        represents the image of an element of the basis of the
        domain.

    - ``category`` -- a category or ``None`` (default: ``None``)
    """

    def __init__(self, domain, function, codomain=None, category=None):
        """
        

        """
        # Caveat: This calls Morphism.__init__ twice ...
        ModuleMorphism.__init__(self, domain, codomain, category=category)
        SetMorphism.__init__(self, self.parent(), function)

class ModuleMorphismByLinearity(ModuleMorphism):
    """
    A class for module morphisms obtained by extending a function by linearity.
    """
    def __init__(self, domain, on_basis=None, codomain=None, category=None,
                 position=0, zero=None):
        """
        Construct a module morphism by linearity.

        INPUT:

        - ``domain`` -- a parent in ``ModulesWithBasis(...)``
        - ``on_basis`` -- a function which accepts indices of the basis of
          ``domain`` as ``position``-th argument (optional)
        - ``codomain`` -- a parent in ``Modules(...)``; defaults to
          ``on_basis.codomain()`` if the latter is defined
        - ``position`` -- a non-negative integer; defaults to 0
        - ``zero`` -- the zero of the codomain; defaults to ``codomain.zero()``

        ``on_basis`` may alternatively be provided in derived classes
        by implementing or setting the attribute ``_on_basis``.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(ZZ, [-2, -1, 1, 2])
            sage: Y = CombinatorialFreeModule(ZZ, [1, 2])
            sage: from sage.modules.module_with_basis_morphism import ModuleMorphismByLinearity
            sage: phi = ModuleMorphismByLinearity(X, on_basis=Y.monomial * abs)

        TESTS::

            sage: TestSuite(phi).run()
        """
        # Might want to assert that domain is a module with basis
        base_ring = domain.base_ring()

        if codomain is None and hasattr(on_basis, 'codomain'):
            codomain = on_basis.codomain()
        if zero is None:
            zero = codomain.zero()
        self._zero = zero
        self._position = position
        if on_basis is not None:
            self._on_basis = on_basis

        self._is_module_with_basis_over_same_base_ring = \
            codomain in ModulesWithBasis( base_ring ) and zero == codomain.zero()

        ModuleMorphism.__init__(self, domain, codomain,
                                category=category,
                                affine=zero != codomain.zero())

    def __eq__(self, other):
        """
        EXAMPLES::

            sage: X = CombinatorialFreeModule(ZZ, [-2, -1, 1, 2])
            sage: Y = CombinatorialFreeModule(ZZ, [1, 2])
            sage: f  = X.module_morphism(on_basis = Y.monomial * abs)
            sage: g  = X.module_morphism(on_basis = Y.monomial * abs)
            sage: h1 = X.module_morphism(on_basis = X.monomial * abs)
            sage: h2 = X.module_morphism(on_basis = X.monomial * factorial)
            sage: h3 = X.module_morphism(on_basis = Y.monomial * abs, category = Modules(ZZ))
            sage: f == g, f == h1, f == h2, f == h3, f == 1, 1 == f
            (True, False, False, False, False, False)
        """
        return self.__class__ is other.__class__ and parent(self) == parent(other) and self.__dict__ == other.__dict__


    def on_basis(self):
        """
        Return the action of this morphism on basis elements, as per
        :meth:`ModulesWithBasis.Homsets.ElementMethods.on_basis`.

        OUTPUT:

        - a function from the indices of the basis of the domain to the
          codomain

        EXAMPLES::

            sage: X = CombinatorialFreeModule(ZZ, [-2, -1, 1, 2])
            sage: Y = CombinatorialFreeModule(ZZ, [1, 2])
            sage: phi_on_basis = Y.monomial * abs
            sage: phi = sage.modules.module_with_basis_morphism.ModuleMorphismByLinearity(X, on_basis = phi_on_basis, codomain = Y)
            sage: x = X.basis()
            sage: phi.on_basis()(-2)
            B[2]
            sage: phi.on_basis() == phi_on_basis
            True
        """
        return self._on_basis

    def __call__(self, *args):
        r"""
        Apply this morphism to ``*args``.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(ZZ, [-2, -1, 1, 2])
            sage: Y = CombinatorialFreeModule(ZZ, [1, 2])
            sage: def phi_on_basis(i): return Y.monomial(abs(i))
            sage: phi = sage.modules.module_with_basis_morphism.ModuleMorphismByLinearity(X, on_basis = Y.monomial * abs, codomain = Y)
            sage: x = X.basis()
            sage: phi(x[1]), phi(x[-2]), phi(x[1] + 3 * x[-2])
            (B[1], B[2], B[1] + 3*B[2])

        .. TODO::

            Add more tests for multi-parameter module morphisms.
        """
        before = args[0:self._position]
        after = args[self._position+1:len(args)]
        x = args[self._position]
        assert(x.parent() is self.domain())

        if self._is_module_with_basis_over_same_base_ring:
            return self.codomain().linear_combination( (self._on_basis(*(before+(index,)+after)), coeff ) for (index, coeff) in args[self._position] )
        else:
            return sum(( coeff * self._on_basis(*(before+(index,)+after)) for (index, coeff) in args[self._position]), self._zero)

    # As per the specs of Map, we should in fact implement _call_.
    # However we currently need to abuse Map.__call__ (which strict
    # type checking) for multi-parameter module morphisms
    # To be cleaned up
    _call_ = __call__

class TriangularModuleMorphism(ModuleMorphism):
    r"""
    An abstract class for triangular module morphisms; that is, module
    morphisms from `X` to `Y` whose representing matrix in the
    distinguished bases of `X` and `Y` is upper triangular with
    invertible elements on its diagonal.

    See :meth:`ModulesWithBasis.ParentMethods.module_morphism`

    INPUT:

    - ``domain`` -- a module `X` with basis `F`
    - ``codomain`` -- a module `Y` with basis `G` (defaults to `X`)
    - ``unitriangular`` -- boolean (default: ``False``)
    - ``triangular`` -- (default: ``"upper"``) ``"upper"`` or ``"lower"``:

      * ``"upper"`` - if the :meth:`leading_support()` of the image of
        `F(i)` is `i`, or
      * ``"lower"`` - if the :meth:`trailing_support()` of the image of
        `F(i)` is `i`

    - ``cmp`` -- an optional comparison function on the index set `J` of
      the basis `G` of the codomain.
    - ``invertible`` -- boolean or ``None`` (default: ``None``); should
      be set to ``True`` if Sage is to compute an inverse for ``self``.
      Automatically set to ``True`` if the domain and codomain share the
      same indexing set and to ``False`` otherwise.
    - ``inverse_on_support`` - compute the inverse on the support if the
      codomain and domain have different index sets. See assumptions
      below.

    Assumptions:

    - `X` and `Y` have the same base ring `R`.

    - Let `I` and `J` be the respective index sets of the bases `F` and
      `G`. Either `I = J`, or ``inverse_on_support`` is a
      function `r : J \to I` with the following property: for any `j \in J`,
      `r(j)` should return an `i \in I` such that the leading term (or
      trailing term, if ``triangular`` is set to ``"lower"``) of
      ``on_basis(i)`` (with respect to the comparison ``cmp``, if the
      latter is set, or just the default comparison otherwise) is `j` if
      there exists such an `i`, or ``None`` if not.

    OUTPUT:

    A morphism from `X` to `Y`.

    .. WARNING::

        This class is meant to be used as complement for a concrete
        class for how the morphism is implemented as a function.  In
        particular, the :meth:`__init__` method focuses on setting up
        the data structure describing the triangularity of the
        morphism. It purposely does *not* call
        :meth:`ModuleMorphism.__init__` which should be called
        (directly or indirectly) before calling this method.

    EXAMPLES:

    We construct and invert an upper unitriangular module morphism between
    two free `\QQ`-modules::

        sage: I = range(1,200)
        sage: X = CombinatorialFreeModule(QQ, I); X.rename("X"); x = X.basis()
        sage: Y = CombinatorialFreeModule(QQ, I); Y.rename("Y"); y = Y.basis()
        sage: f = Y.sum_of_monomials * divisors   # This * is map composition.
        sage: phi = X.module_morphism(f, unitriangular="upper", codomain = Y)
        sage: phi(x[2])
        B[1] + B[2]
        sage: phi(x[6])
        B[1] + B[2] + B[3] + B[6]
        sage: phi(x[30])
        B[1] + B[2] + B[3] + B[5] + B[6] + B[10] + B[15] + B[30]
        sage: phi.preimage(y[2])
        -B[1] + B[2]
        sage: phi.preimage(y[6])
        B[1] - B[2] - B[3] + B[6]
        sage: phi.preimage(y[30])
        -B[1] + B[2] + B[3] + B[5] - B[6] - B[10] - B[15] + B[30]
        sage: (phi^-1)(y[30])
        -B[1] + B[2] + B[3] + B[5] - B[6] - B[10] - B[15] + B[30]

    A lower triangular (but not unitriangular) morphism::

        sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
        sage: def ut(i): return sum(j*x[j] for j in range(i,4))
        sage: phi = X.module_morphism(ut, triangular="lower", codomain = X)
        sage: phi(x[2])
        2*B[2] + 3*B[3]
        sage: phi.preimage(x[2])
        1/2*B[2] - 1/2*B[3]
        sage: phi(phi.preimage(x[2]))
        B[2]

    Using the ``cmp`` keyword, we can use triangularity even if
    the map becomes triangular only after a permutation of the basis::

        sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
        sage: def vt(i): return (x[1] + x[2] if i == 1 else x[2] + (x[3] if i == 3 else 0))
        sage: perm = [0, 2, 1, 3]
        sage: phi = X.module_morphism(vt, triangular="upper", codomain = X,
        ....:                         cmp=lambda a, b: cmp(perm[a], perm[b]))
        sage: [phi(x[i]) for i in range(1, 4)]
        [B[1] + B[2], B[2], B[2] + B[3]]
        sage: [phi.preimage(x[i]) for i in range(1, 4)]
        [B[1] - B[2], B[2], -B[2] + B[3]]

    The same works in the lower-triangular case::

        sage: def wt(i): return (x[1] + x[2] + x[3] if i == 2 else x[i])
        sage: phi = X.module_morphism(wt, triangular="lower", codomain = X,
        ....:                         cmp=lambda a, b: cmp(perm[a], perm[b]))
        sage: [phi(x[i]) for i in range(1, 4)]
        [B[1], B[1] + B[2] + B[3], B[3]]
        sage: [phi.preimage(x[i]) for i in range(1, 4)]
        [B[1], -B[1] + B[2] - B[3], B[3]]

    An injective but not surjective morphism cannot be inverted,
    but the ``inverse_on_support`` keyword allows Sage to find a
    partial inverse::

        sage: X = CombinatorialFreeModule(QQ, [1,2,3]); x = X.basis()
        sage: Y = CombinatorialFreeModule(QQ, [1,2,3,4,5]); y = Y.basis()
        sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  )
        sage: phi = X.module_morphism(uut, codomain = Y,
        ....:        unitriangular="lower",
        ....:        inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
        sage: phi(x[2])
        B[3] + B[4] + B[5]
        sage: phi.preimage(y[3])
        B[2] - B[3]

    The ``inverse_on_support`` keyword can also be used if the
    bases of the domain and the codomain are identical but one of
    them has to be permuted in order to render the morphism
    triangular. For example::

        sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
        sage: def zt(i):
        ....:     return (x[3] if i == 1 else x[1] if i == 2
        ....:             else x[1] + x[2])
        sage: def perm(i):
        ....:     return (2 if i == 1 else 3 if i == 2 else 1)
        sage: phi = X.module_morphism(zt, triangular="upper", codomain = X,
        ....:                         inverse_on_support=perm)
        sage: [phi(x[i]) for i in range(1, 4)]
        [B[3], B[1], B[1] + B[2]]
        sage: [phi.preimage(x[i]) for i in range(1, 4)]
        [B[2], -B[2] + B[3], B[1]]

    The same works if the permutation induces lower triangularity::

        sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
        sage: def zt(i):
        ....:     return (x[3] if i == 1 else x[2] if i == 2
        ....:             else x[1] + x[2])
        sage: def perm(i):
        ....:     return 4 - i
        sage: phi = X.module_morphism(zt, triangular="lower", codomain = X,
        ....:                         inverse_on_support=perm)
        sage: [phi(x[i]) for i in range(1, 4)]
        [B[3], B[2], B[1] + B[2]]
        sage: [phi.preimage(x[i]) for i in range(1, 4)]
        [-B[2] + B[3], B[2], B[1]]

    The ``inverse_on_basis`` and ``cmp`` keywords can be combined::

        sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
        sage: def zt(i):
        ....:     return (2*x[2] + 3*x[3] if i == 1
        ....:             else x[1] + x[2] + x[3] if i == 2
        ....:             else 4*x[2])
        sage: def perm(i):
        ....:     return (2 if i == 1 else 3 if i == 2 else 1)
        sage: perverse_cmp = lambda a, b: cmp((a-2) % 3, (b-2) % 3)
        sage: phi = X.module_morphism(zt, triangular="upper", codomain = X,
        ....:                         inverse_on_support=perm, cmp=perverse_cmp)
        sage: [phi(x[i]) for i in range(1, 4)]
        [2*B[2] + 3*B[3], B[1] + B[2] + B[3], 4*B[2]]
        sage: [phi.preimage(x[i]) for i in range(1, 4)]
        [-1/3*B[1] + B[2] - 1/12*B[3], 1/4*B[3], 1/3*B[1] - 1/6*B[3]]
    """
    def __init__(self, triangular="upper", unitriangular=False,
                 cmp=None, inverse=None, inverse_on_support=None, invertible=None):
        """
        TESTS::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
            sage: def ut(i): return sum(j*x[j] for j in range(i,4))
            sage: import __main__; __main__.ut = ut
            sage: phi = X.module_morphism(ut, triangular="lower", codomain = X)
            sage: phi.__class__
            <class 'sage.modules.module_with_basis_morphism.TriangularModuleMorphismByLinearity_with_category'>
            sage: TestSuite(phi).run(skip=["_test_pickling"])

        Known issue::

            sage: loads(dumps(phi)) == phi
            False

        This is due to one of the attributes not being picklable::

            sage: c = phi._inverse_on_support_precomputed
            sage: c
            Cached version of <function _inverse_on_support_precomputed at ...>
            sage: loads(dumps(c)) == c
            False
        """
        if triangular == "upper":
            self._dominant_item = attrcall("leading_item",  cmp)
        else:
            self._dominant_item = attrcall("trailing_item", cmp)
        # We store those two just be able to pass them down to the inverse function
        self._triangular = triangular
        self._cmp = cmp

        domain = self.domain()
        codomain = self.codomain()
        self._unitriangular = unitriangular
        self._inverse = inverse
        if inverse_on_support == "compute":
            self._inverse_on_support = self._inverse_on_support_precomputed
            for i in self.domain().basis().keys():
                (j, c) = self._dominant_item(self._on_basis(i))
                self._inverse_on_support.set_cache(i, j)
        elif inverse_on_support is None:
            self._inverse_on_support = self._inverse_on_support_trivial
        else:
            self._inverse_on_support = inverse_on_support
        if invertible is not None:
            self._invertible = invertible
        else:
            self._invertible = (domain.basis().keys() == codomain.basis().keys())

    def _inverse_on_support_trivial(self, i):
        return i

    @cached_method
    def _inverse_on_support_precomputed(self, i):
        return None

    def _test_triangular(self, **options):
        """
        Test that ``self`` is actually triangular

        See also: :class:`sage.misc.sage_unittest.TestSuite`.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); y = Y.basis()
            sage: f = lambda i: sum(  y[j] for j in range(i,4)  )
            sage: phi = X.module_morphism(f, triangular="lower", codomain=Y)
            sage: phi._test_triangular()

            sage: fw = lambda i: sum(  y[j] for j in range(i+1,4)  )
            sage: phi = X.module_morphism(fw, triangular="lower", codomain=Y)
            sage: phi._test_triangular()
            Traceback (most recent call last):
            ...
            AssertionError: morphism is not triangular on 1

            sage: X = CombinatorialFreeModule(QQ, [1,2,3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1,2,3,4,5]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  )
            sage: phi = X.module_morphism(uut, codomain=Y,
            ....:      unitriangular="lower",
            ....:      inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phi._test_triangular()

            sage: ut = lambda i: sum(  2*y[j] for j in range(i+1,6)  )
            sage: phi = X.module_morphism(ut, codomain=Y,
            ....:      unitriangular="lower",
            ....:      inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phi._test_triangular()
            Traceback (most recent call last):
            ...
            AssertionError: morphism is not unitriangular on 1
        """
        from sage.misc.lazy_format import LazyFormat
        tester = self._tester(**options)
        for x in self.domain().basis().keys():
            # or should it be self.domain().basis().some_elements() # ?
            bs, co = self._dominant_item(self._on_basis(x))
            if self._unitriangular:
                tester.assertEqual(co, self.domain().base_ring().one(),
                    LazyFormat("morphism is not unitriangular on %s")%(x))
            xback = self._inverse_on_support(bs)
            tester.assertEqual(x, xback,
                LazyFormat("morphism is not triangular on %s")%(x))


    def _on_basis(self, i):
        """
        Return the image by ``self`` of the basis element indexed by ``i``.

        TESTS::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); y = Y.basis()
            sage: f = lambda i: sum(  y[j] for j in range(i,4)  )
            sage: phi = X.module_morphism(f, triangular="lower", codomain = Y)
            sage: phi._on_basis(2)
            B[2] + B[3]
        """
        return self.on_basis(i)

    def __invert__(self):
        """
        Return the triangular morphism which is the inverse of ``self``.

        Raises an error if ``self`` is not invertible.

        TESTS::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(1,i+1)) # uni-upper
            sage: ult = lambda i: sum(  y[j] for j in range(i,4)  ) # uni-lower
            sage: ut =  lambda i: sum(j*y[j] for j in range(1,i+1)) # upper
            sage: lt =  lambda i: sum(j*y[j] for j in range(i,4  )) # lower
            sage: f_uut = X.module_morphism(uut, codomain=Y,
            ....:                           unitriangular="upper")
            sage: f_ult = X.module_morphism(ult, codomain=Y,
            ....:                           unitriangular="lower")
            sage: f_ut  = X.module_morphism(ut, codomain=Y, triangular="upper")
            sage: f_lt  = X.module_morphism(lt, codomain=Y, triangular="lower")
            sage: (~f_uut)(y[2])
            -B[1] + B[2]
            sage: (~f_ult)(y[2])
            B[2] - B[3]
            sage: (~f_ut)(y[2])
            -1/2*B[1] + 1/2*B[2]
            sage: (~f_lt)(y[2])
            1/2*B[2] - 1/2*B[3]
        """
        if not self._invertible:
            raise ValueError("Non invertible morphism")
        else:
            return self.section()

    def section(self):
        """
        Return the section (partial inverse) of ``self``.

        Return a partial triangular morphism which is a section of
        ``self``. The section morphism raise a ``ValueError`` if asked to
        apply on an element which is not in the image of ``self``.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(QQ, [1,2,3]); x = X.basis()
            sage: X.rename('X')
            sage: Y = CombinatorialFreeModule(QQ, [1,2,3,4,5]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y,
            ....:      inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: ~phi
            Traceback (most recent call last):
            ...
            ValueError: Non invertible morphism
            sage: phiinv = phi.section()
            sage: map(phiinv*phi, X.basis().list()) == X.basis().list()
            True
            sage: phiinv(Y.basis()[1])
            Traceback (most recent call last):
            ...
            ValueError: B[1] is not in the image
        """
        if self._inverse is not None:
            return self._inverse
        if self._inverse_on_support == self._inverse_on_support_trivial:
            retract_dom = None
        else:
            def retract_dom(i):
                self._dominant_item(self._on_basis(i))[0]

        if self._invertible:
            return self.__class__(
                domain=self.codomain(),
                on_basis=self._invert_on_basis,
                codomain=self.domain(), category=self.category_for(),
                unitriangular=self._unitriangular,  triangular=self._triangular,
                cmp=self._cmp, inverse=self,
                inverse_on_support=retract_dom, invertible = self._invertible)
        else:
            return SetMorphism(Hom(self.codomain(), self.domain(),
                                   SetsWithPartialMaps()),
                               self.preimage)

    # This should be removed and optimized as soon as triangular
    # morphism not defined by linearity are available
    # (the inverse should not be computed on the basis).
    def _invert_on_basis(self, i):
        r"""
        Return the image, by the inverse of ``self``, of the basis element
        indexed by ``i``.

        TESTS::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i,4)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y)
            sage: phi._invert_on_basis(2)
            B[2] - B[3]
        """
        return self.preimage( self.codomain().monomial(i) )

    def preimage(self, f):
        """
        Return the preimage of `f` under ``self``.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i,4)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y)
            sage: phi.preimage(y[1] + y[2])
            B[1] - B[3]

        The morphism need not be surjective. In the following example,
        the codomain is of larger dimension than the domain::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3, 4]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i,5)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y)
            sage: phi.preimage(y[1] + y[2])
            B[1] - B[3]

        Here are examples using ``inverse_on_support`` to handle a
        morphism that shifts the leading indices by `1`::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3, 4, 5]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y,
            ....:         inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phi(x[1])
            B[2] + B[3] + B[4] + B[5]
            sage: phi(x[3])
            B[4] + B[5]
            sage: phi.preimage(y[2] + y[3])
            B[1] - B[3]
            sage: phi(phi.preimage(y[2] + y[3])) == y[2] + y[3]
            True
            sage: el = x[1] + 3*x[2] + 2*x[3]
            sage: phi.preimage(phi(el)) == el
            True

            sage: phi.preimage(y[1])
            Traceback (most recent call last):
            ...
            ValueError: B[1] is not in the image
            sage: phi.preimage(y[4])
            Traceback (most recent call last):
            ...
            ValueError: B[4] is not in the image

        Over a base ring like `\ZZ`, the morphism can be non
        surjective even when the dimensions match::

            sage: X = CombinatorialFreeModule(ZZ, [1, 2, 3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(ZZ, [1, 2, 3]); y = Y.basis()
            sage: uut = lambda i: sum( 2* y[j] for j in range(i,4)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y)
            sage: phi.preimage(2*y[1] + 2*y[2])
            B[1] - B[3]

        The error message in case of failure could be more specific though::

            sage: phi.preimage(y[1] + y[2])
            Traceback (most recent call last):
              ...
            TypeError: no conversion of this rational to integer
        """
        F = self.domain()
        G = self.codomain()
        basis_map = self._on_basis
        if not f in G:
            raise ValueError("f(={}) must be in the codomain of the morphism to have a preimage under the latter".format(f))

        remainder = f

        out = F.zero()
        while not remainder.is_zero():
            (j,c) = self._dominant_item(remainder)

            j_preimage = self._inverse_on_support(j)
            if j_preimage is None:
                raise ValueError("{} is not in the image".format(f))
            s = basis_map(j_preimage)
            if not j == self._dominant_item(s)[0]:
                raise ValueError("The morphism (={}) is not triangular at {}, and therefore a preimage cannot be computed".format(f, s))

            if not self._unitriangular:
                # What's the appropriate way to request an exact
                # division within the base ring and get an error if
                # this is not possible?
                c = c.parent()(c / s[j])

            remainder -= s._lmul_(c)
            out += F.term(j_preimage, c)

        return out

    def coreduced(self, y):
        """
        Return `y` reduced w.r.t. the image of ``self``.

        INPUT:

        - ``self`` -- a triangular morphism over a field, or a
          unitriangular morphism over a ring
        - ``y`` -- an element of the codomain of ``self``

        Suppose that ``self`` is a morphism from `X` to `Y`. Then, for
        any `y \in Y`, the call ``self.coreduced(y)`` returns a
        normal form for `y` in the quotient `Y / I` where `I` is the
        image of ``self``.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(QQ, [1,2,3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1,2,3,4,5]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  )
            sage: phi = X.module_morphism(uut, codomain = Y,
            ....:        unitriangular="lower",
            ....:        inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: [phi(v) for v in X.basis()]
            [B[2] + B[3] + B[4] + B[5],
                    B[3] + B[4] + B[5],
                           B[4] + B[5]]
            sage: [phi.coreduced(y[1]-2*y[4])]
            [B[1] + 2*B[5]]
            sage: [phi.coreduced(v) for v in y]
            [B[1], 0, 0, -B[5], B[5]]

        Now with a non uni-triangular morphism::

            sage: ut = lambda i: sum( j*y[j] for j in range(i+1,6)  )
            sage: phi = X.module_morphism(ut, codomain = Y,
            ....:       triangular="lower",
            ....:       inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: [phi(v) for v in X.basis()]
            [2*B[2] + 3*B[3] + 4*B[4] + 5*B[5],
                      3*B[3] + 4*B[4] + 5*B[5],
                               4*B[4] + 5*B[5]]
            sage: [phi.coreduced(y[1]-2*y[4])]
            [B[1] + 5/2*B[5]]
            sage: [phi.coreduced(v) for v in y]
            [B[1], 0, 0, -5/4*B[5], B[5]]

        For general rings, this method is only implemented for
        unitriangular morphisms::

            sage: X = CombinatorialFreeModule(ZZ, [1,2,3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(ZZ, [1,2,3,4,5]); y = Y.basis()
            sage: phi = X.module_morphism(uut, codomain = Y,
            ....:       unitriangular="lower",
            ....:       inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: [phi.coreduced(y[1]-2*y[4])]
            [B[1] + 2*B[5]]
            sage: [phi.coreduced(v) for v in y]
            [B[1], 0, 0, -B[5], B[5]]

            sage: phi = X.module_morphism(ut, codomain = Y,
            ....:       triangular="lower",
            ....:       inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: [phi.coreduced(v) for v in y]
            Traceback (most recent call last):
            ...
            NotImplementedError: coreduce for a triangular but not unitriangular morphism over a ring

        .. NOTE:: Before :trac:`8678` this method used to be called co_reduced.
        """
        G = self.codomain()
        if G.base_ring() not in Fields and not self._unitriangular:
            raise NotImplementedError, "coreduce for a triangular but not unitriangular morphism over a ring"
        basis_map = self._on_basis
        assert y in G

        result    = G.zero()
        remainder = y

        while not remainder.is_zero():
            (j,c) = self._dominant_item(remainder)
            j_preimage = self._inverse_on_support(j)
            if j_preimage is None:
                dom_term = G.term(j,c)
                remainder -= dom_term
                result += dom_term
            else:
                s = basis_map(j_preimage)
                assert j == self._dominant_item(s)[0]
                if not self._unitriangular:
                    c = c / s[j]  # the base ring is a field
                remainder -= s._lmul_(c)
        return result
    co_reduced = deprecated_function_alias(8678, coreduced)

    def cokernel_basis_indices(self):
        """
        Return the indices of the natural monomial basis of the cokernel of ``self``.

        INPUT:

        - ``self`` -- a triangular morphism over a field or a
          unitriangular morphism over a ring, with a finite
          dimensional codomain.

        OUTPUT:

        A list `E` of indices of the basis `(B_e)_e` of the codomain
        of ``self`` so that `(B_e)_{e\in E}` forms a basis of a
        supplementary of the image set of ``self``.

        Thinking of this triangular morphism as a row echelon matrix,
        this returns the complementary of the characteristic
        columns. Namely `E` is the set of indices which do not appear
        as leading support of some element of the image set of
        ``self``.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(ZZ, [1,2,3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(ZZ, [1,2,3,4,5]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  ) # uni-upper
            sage: phi = X.module_morphism(uut, unitriangular="upper", codomain = Y,
            ....:       inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phi.cokernel_basis_indices()
            [1, 5]

            sage: phi = X.module_morphism(uut, triangular="upper", codomain = Y,
            ....:       inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phi.cokernel_basis_indices()
            Traceback (most recent call last):
            ...
            NotImplementedError: cokernel_basis_indices for a triangular but not unitriangular morphism over a ring

            sage: Y = CombinatorialFreeModule(ZZ, NN); y = Y.basis()
            sage: phi = X.module_morphism(uut, unitriangular="upper", codomain = Y,
            ....:       inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phi.cokernel_basis_indices()
            Traceback (most recent call last):
            ...
            NotImplementedError: cokernel_basis_indices implemented only for morphisms with a finite dimensional codomain
        """
        R = self.domain().base_ring()
        if R not in Fields and not self._unitriangular:
            raise NotImplementedError, "cokernel_basis_indices for a triangular but not unitriangular morphism over a ring"
        if self.codomain() not in Modules(R).FiniteDimensional():
            raise NotImplementedError, "cokernel_basis_indices implemented only for morphisms with a finite dimensional codomain"
        return [i for i in self.codomain().basis().keys() if self._inverse_on_support(i) is None]

    def cokernel_projection(self, category = None):
        """
        Return a projection on the co-kernel of ``self``.

        INPUT:

        - ``category`` -- the category of the result

        EXAMPLES::

            sage: X = CombinatorialFreeModule(QQ, [1,2,3]); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1,2,3,4,5]); y = Y.basis()
            sage: uut = lambda i: sum(  y[j] for j in range(i+1,6)  ) # uni-upper
            sage: phi = X.module_morphism(uut, triangular=True, codomain = Y,
            ....:      inverse_on_support=lambda i: i-1 if i in [2,3,4] else None)
            sage: phipro = phi.cokernel_projection()
            sage: phipro(y[1] + y[2])
            B[1]
            sage: all(phipro(phi(x)).is_zero() for x in X.basis())
            True
            sage: phipro(y[1])
            B[1]
            sage: phipro(y[4])
            -B[5]
            sage: phipro(y[5])
            B[5]
        """
        codomain = self.codomain()
        category = ModulesWithBasis(codomain.base_ring()).or_subcategory(category)
        return codomain.module_morphism(function=self.coreduced,
                                        codomain=codomain, category=category)

    co_kernel_projection = deprecated_function_alias(8678, cokernel_projection)

class TriangularModuleMorphismByLinearity(ModuleMorphismByLinearity, TriangularModuleMorphism):
    def __init__(self, domain, on_basis, codomain=None, category=None, **keywords):
        ModuleMorphismByLinearity.__init__(self, on_basis=on_basis,
                                           domain=domain, codomain=codomain, category=category)
        TriangularModuleMorphism.__init__(self, **keywords)

class TriangularModuleMorphismFromFunction(ModuleMorphismFromFunction, TriangularModuleMorphism):
    def __init__(self, domain, function, codomain=None, category=None, **keywords):
        ModuleMorphismFromFunction.__init__(self, function=function,
                                          domain=domain, codomain=codomain, category=category)
        TriangularModuleMorphism.__init__(self, **keywords)


class ModuleMorphismFromMatrix(ModuleMorphismByLinearity):
    r"""
    A class for module morphisms built from from their matrix in the
    distinguished bases of the domain and codomain.

    .. SEEALSO:

        - :meth:`ModulesWithBasis.ParentMethods.module_morphism`.
        - :meth:`ModulesWithBasis.FiniteDimensional.MorphismMethods.matrix`

    INPUT:

    - ``domain``, ``codomain`` -- two finite dimensional modules over
      the same base ring `R` with basis `F` and `G`, respectively

    - ``matrix`` -- a matrix with base ring `R` and dimensions
      matching that of `F` and `G` respectively

    - ``side`` -- "left" or "right" (default: "left")

        If ``side`` is "left", this morphism is considered as
        acting on the left; i.e. each column of the matrix
        represents the image of an element of the basis of the
        domain.

    - ``category`` -- a category or ``None`` (default: ``None``)

    EXAMPLES::

        sage: X = CombinatorialFreeModule(ZZ, [1,2]); X.rename("X"); x = X.basis()
        sage: Y = CombinatorialFreeModule(ZZ, [3,4]); Y.rename("Y"); y = Y.basis()
        sage: m = matrix([[1,2],[3,5]])
        sage: phi = X.module_morphism(matrix=m, codomain=Y)
        sage: phi.parent()
        Set of Morphisms from X to Y in Category of finite dimensional modules with basis over Integer Ring
        sage: phi.__class__
        <class 'sage.modules.module_with_basis_morphism.ModuleMorphismFromMatrix_with_category'>
        sage: phi(x[1])
        B[3] + 3*B[4]
        sage: phi(x[2])
        2*B[3] + 5*B[4]

        sage: m = matrix([[1,2],[3,5]])
        sage: phi = X.module_morphism(matrix=m, codomain=Y, side="right", category=Modules(ZZ).WithBasis())
        sage: phi.parent()
        Set of Morphisms from X to Y in Category of modules with basis over Integer Ring
        sage: phi(x[1])
        B[3] + 2*B[4]
        sage: phi(x[2])
        3*B[3] + 5*B[4]

    .. TODO:

        - Possibly implement rank, addition, multiplication, matrix,
          etc, from the stored matrix
        - Pickling: the attribute _on_basis = d.__getitem__ is not picklable.
          This is probably best implemented by pickling by construction.
    """
    def __init__(self, domain, matrix, codomain=None, category=None, side="left"):
        r"""
        Initialize ``self``.

        TESTS::

            sage: from sage.modules.module_with_basis_morphism import ModuleMorphismFromMatrix
            sage: X = CombinatorialFreeModule(ZZ, [1,2]); X.rename("X"); x = X.basis()
            sage: Y = CombinatorialFreeModule(ZZ, [3,4]); Y.rename("Y"); y = Y.basis()
            sage: m = matrix([[1,2],[3,5]])
            sage: phi = ModuleMorphismFromMatrix(matrix=m, domain=X, codomain=Y, side="right")
            sage: phi.__class__
            <class 'sage.modules.module_with_basis_morphism.ModuleMorphismFromMatrix_with_category'>
            sage: phi.matrix(side="right") == m
            True
            sage: TestSuite(phi).run(skip=["_test_pickling"])

        The matrix is stored in the morphism, as for an action on the right::

            sage: phi._matrix
            [1 2]
            [3 5]

            sage: phi = ModuleMorphismFromMatrix(matrix=m, domain=X, codomain=Y, side="left")
            sage: phi._matrix
            [1 3]
            [2 5]
        """
        C = ModulesWithBasis(domain.base_ring()).FiniteDimensional()
        if not domain in C:
            raise ValueError("The domain %s should be finite dimensional"%domain)
        if codomain is None:
            raise ValueError("The codomain %s should be specified")
        if not codomain in C:
            raise ValueError("The codomain %s should be finite dimensional"%codomain)
        import sage.combinat.ranker
        indices = tuple(domain.basis().keys())
        rank_domain  = sage.combinat.ranker.rank_from_list(indices)
        if side == "left":
            matrix = matrix.transpose()
        if matrix.nrows() != len(indices):
            raise ValueError("The dimension of the matrix (%s) does not match with the dimension of the domain (%s)"
                             %(matrix.nrows(), len(indices)))
        if matrix.ncols() != codomain.dimension():
            raise ValueError("The dimension of the matrix (%s) does not match with the dimension of the codomain (%s)"
                             %(matrix.ncols(), codomain.dimension()))
        self._matrix = matrix
        d = { xt: codomain.from_vector(matrix.row(rank_domain(xt)))
              for xt in domain.basis().keys() }

        ModuleMorphismByLinearity.__init__(self, on_basis=d.__getitem__,
                                           domain=domain, codomain=codomain,
                                           category=category)

class DiagonalModuleMorphism(ModuleMorphismByLinearity):
    r"""
    A class for diagonal module morphisms.

    See :meth:`ModulesWithBasis.ParentMethods.module_morphism`.

    INPUT:

    - ``domain``, ``codomain`` -- two modules with basis `F` and `G`,
      respectively
    - ``diagonal`` -- a function `d`

    Assumptions:

    - ``domain`` and ``codomain`` have the same base ring `R`,
    - their respective bases `F` and `G` have the same index set `I`,
    - `d` is a function `I \to R`.

    Return the diagonal module morphism from ``domain`` to ``codomain``
    sending `F(i) \mapsto d(i) G(i)` for all `i \in I`.

    By default, ``codomain`` is currently assumed to be ``domain``.
    (Todo: make a consistent choice with ``*ModuleMorphism``.)

    .. TODO::

        - Implement an optimized ``_call_()`` function.
        - Generalize to a mapcoeffs.
        - Generalize to a mapterms.

    EXAMPLES::

        sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X")
        sage: phi = X.module_morphism(diagonal = factorial, codomain = X)
        sage: x = X.basis()
        sage: phi(x[1]), phi(x[2]), phi(x[3])
        (B[1], 2*B[2], 6*B[3])
    """
    def __init__(self, domain, diagonal, codomain = None, category = None):
        r"""
        Initialize ``self``.

        TESTS::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X")
            sage: phi = X.module_morphism(diagonal = factorial, codomain = X)
            sage: phi.__class__
            <class 'sage.modules.module_with_basis_morphism.DiagonalModuleMorphism_with_category'>
            sage: TestSuite(phi).run()
        """
        assert codomain is not None
        assert domain.basis().keys() == codomain.basis().keys()
        assert domain.base_ring()    == codomain.base_ring()
        if category is None:
            category = ModulesWithBasis(domain.base_ring())
        ModuleMorphismByLinearity.__init__(
            self, domain=domain, codomain=codomain, category=category)
        self._diagonal = diagonal

    def _on_basis(self, i):
        """
        Return the image by ``self`` of the basis element indexed by ``i``.

        TESTS::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); Y.rename("Y"); y = Y.basis()
            sage: phi = X.module_morphism(diagonal = factorial, codomain = X)
            sage: phi._on_basis(3)
            6*B[3]
        """
        return self.codomain().term(i, self._diagonal(i))

    def __invert__(self):
        """
        Return the inverse diagonal morphism.

        EXAMPLES::

            sage: X = CombinatorialFreeModule(QQ, [1, 2, 3]); X.rename("X"); x = X.basis()
            sage: Y = CombinatorialFreeModule(QQ, [1, 2, 3]); Y.rename("Y"); y = Y.basis()
            sage: phi = X.module_morphism(diagonal = factorial, codomain = X)
            sage: phi_inv = ~phi
            sage: phi_inv
            Generic endomorphism of Y
            sage: phi_inv(y[3])
            1/6*B[3]

        Caveat: this inverse morphism is only well defined if
        `d(\lambda)` is always invertible in the base ring. This is
        condition is *not* tested for, so using an ill defined inverse
        morphism will trigger arithmetic errors.
        """
        return self.codomain().module_morphism(
            diagonal=pointwise_inverse_function(self._diagonal),
            codomain=self.domain(), category = self.category_for())


def pointwise_inverse_function(f):
    r"""
    Return the function `x \mapsto 1 / f(x)`.

    INPUT:

    - ``f`` -- a function

    EXAMPLES::

        sage: from sage.modules.module_with_basis_morphism import pointwise_inverse_function
        sage: def f(x): return x
        ....:
        sage: g = pointwise_inverse_function(f)
        sage: g(1), g(2), g(3)
        (1, 1/2, 1/3)

    :func:`pointwise_inverse_function` is an involution::

        sage: f is pointwise_inverse_function(g)
        True

    .. TODO::

        This has nothing to do here!!! Should there be a library for
        pointwise operations on functions somewhere in Sage?
    """
    if hasattr(f, "pointwise_inverse"):
        return f.pointwise_inverse()
    return PointwiseInverseFunction(f)

from sage.structure.sage_object import SageObject
class PointwiseInverseFunction(SageObject):
    r"""
    A class for pointwise inverse functions.

    The pointwise inverse function of a function `f` is the function
    sending every `x` to `1 / f(x)`.

    EXAMPLES::

        sage: from sage.modules.module_with_basis_morphism import PointwiseInverseFunction
        sage: f = PointwiseInverseFunction(factorial)
        sage: f(0), f(1), f(2), f(3)
        (1, 1, 1/2, 1/6)
    """

    def __eq__(self, other):
        """
        TESTS::

            sage: from sage.modules.module_with_basis_morphism import PointwiseInverseFunction
            sage: f = PointwiseInverseFunction(factorial)
            sage: g = PointwiseInverseFunction(factorial)
            sage: f is g
            False
            sage: f == g
            True
        """
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__

    def __init__(self, f):
        """
        TESTS::

            sage: from sage.modules.module_with_basis_morphism import PointwiseInverseFunction
            sage: f = PointwiseInverseFunction(factorial)
            sage: f(0), f(1), f(2), f(3)
            (1, 1, 1/2, 1/6)
            sage: TestSuite(f).run()
        """
        self._pointwise_inverse = f

    def __call__(self, *args):
        """
        TESTS::

            sage: from sage.modules.module_with_basis_morphism import PointwiseInverseFunction
            sage: g = PointwiseInverseFunction(operator.mul)
            sage: g(5,7)
            1/35
        """
        return ~(self._pointwise_inverse(*args))

    def pointwise_inverse(self):
        """
        TESTS::

            sage: from sage.modules.module_with_basis_morphism import PointwiseInverseFunction
            sage: g = PointwiseInverseFunction(operator.mul)
            sage: g.pointwise_inverse() is operator.mul
            True
        """
        return self._pointwise_inverse
