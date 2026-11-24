"""Public result objects for the pyhygrothermfem_fairyfly session API.

``InspectionReport`` answers questions about an archive without solving it
(inspect semantics); ``SolvedResult`` is the in-memory handle returned by
``solve`` (lazy access to computed members). Report objects are never
returned by ``solve``/``run_thmz`` -- failures there are exceptions.
"""
import json


class InspectionIssue:
    """One validation issue: a stable code plus a human-readable message.

    Attributes:
        code: ``THMZ-Exxxx`` code aligned with docs/thmz-contract.md.
        message: Description of the violated rule.
        member: Archive member the issue belongs to, when identifiable.
    """

    __slots__ = ('code', 'message', 'member')

    def __init__(self, code, message, member=None):
        self.code = code
        self.message = message
        self.member = member

    def __repr__(self):
        return 'InspectionIssue(code={!r}, member={!r})'.format(
            self.code, self.member)


class InspectionReport:
    """Structured inspection result for a THMZ archive.

    Attributes:
        members: Tuple of archive member names in stored order.
        contract_version: Integer ``major * 1000 + minor`` found in
            ``pyHygroTherm.json``, or None for unsolved archives.
        solver_version: Integer solver release number, or None.
        mode: Declared ``CalculationMode`` string, or None when unknown.
        errors: Tuple of InspectionIssue; non-empty means the archive cannot
            be solved. Currently fail-fast: at most one issue.
        warnings: Tuple of InspectionIssue for non-fatal observations.
        input_sha256: Digest of the input archive bytes.
    """

    __slots__ = ('members', 'contract_version', 'solver_version', 'mode',
                 'errors', 'warnings', 'input_sha256')

    def __init__(self, members, contract_version=None, solver_version=None,
                 mode=None, errors=(), warnings=(), input_sha256=None):
        self.members = members
        self.contract_version = contract_version
        self.solver_version = solver_version
        self.mode = mode
        self.errors = errors
        self.warnings = warnings
        self.input_sha256 = input_sha256

    @property
    def ok(self):
        """True when the archive can be fed to solve/run_thmz."""
        return not self.errors

    def __repr__(self):
        return ('InspectionReport(members={}, contract_version={}, mode={}, '
                'errors={}, warnings={})').format(
                    len(self.members), self.contract_version, self.mode,
                    len(self.errors), len(self.warnings))


class SolvedResult:
    """In-memory result handle returned by ``solve``.

    Field values are already computed; result members serialize lazily so a
    consumer that only needs temperatures never pays for XML emission.

    Properties:
        mode: Solve mode string (``dry-steady``, ``dry-transient`` or
            ``hygrothermal-transient``).
        temperatures: Final node temperatures in Celsius, mesh node order.
        heat_fluxes: ``(x, y)`` final nodal heat flux tuples in W/m2.
        energy_error_percent: Recovery-based estimate (steady solves only),
            or None.
        provenance: The ``pyHygroTherm.json`` provenance mapping.
        steps_completed: Solved timestep count for transient solves, else
            None.
        boundary_heat_rates: Per exterior-edge outward heat rates for
            steady solves, else None.
        mesh_results_xml / steady_state_results_xml: Serialized steady
            result members (None for transient solves).
        members: Complete output archive as a name-to-bytes mapping;
            transient solves carry the streamed ``transient results/*``
            members.
    """

    __slots__ = ('mode', 'temperatures', 'heat_fluxes', 'energy_error_percent',
                 'provenance', '_members', '_mesh_results_xml',
                 '_u_factor_results_xml', '_builders', '_nodes', '_case',
                 '_expected_tags', '_edge_outward', '_quads',
                 '_boundary_heat_rates', '_transient')

    def __init__(self, mode, temperatures, heat_fluxes, energy_error_percent,
                 provenance, members, builders, private, transient=None):
        self.mode = mode
        self.temperatures = temperatures
        self.heat_fluxes = heat_fluxes
        self.energy_error_percent = energy_error_percent
        self.provenance = provenance
        self._members = members
        self._builders = builders
        self._mesh_results_xml = None
        self._u_factor_results_xml = None
        (self._nodes, self._case, self._expected_tags,
         self._edge_outward, self._quads) = private
        self._boundary_heat_rates = None
        self._transient = transient

    @property
    def steps_completed(self):
        """Number of solved transient timesteps (None for steady solves)."""
        if self._transient is None:
            return None
        return self._transient['num_steps']

    @property
    def boundary_heat_rates(self):
        """Per exterior-edge outward heat rates (steady solves only).

        Returns:
            Tuple of ``(node1, node2, rate)`` records, one per mesh edge
            that carries an active boundary condition: node1/node2 are
            0-based mesh node positions (the unordered pair, min first),
            rate is the outward integrated heat rate in W/m per unit
            depth (positive when heat leaves the domain). Edges without
            an active condition are absent; adiabatic edges appear only
            when the archive declares them with h=0 convection (rate 0).
            ``None`` for transient solves (per-step edge rates are in the
            ``transient results/*Edges.csv`` members instead).
        """
        if self._transient is not None:
            return None
        if self._boundary_heat_rates is None:
            from .run import _edge_outward_rates
            self._boundary_heat_rates = tuple(
                (edge[0], edge[1], rate)
                for edge, rate in _edge_outward_rates(
                    self._edge_outward, self._nodes, self._quads,
                    self.heat_fluxes, self.temperatures))
        return self._boundary_heat_rates

    def _materialize(self):
        if self._transient is not None or self._mesh_results_xml is not None:
            return
        self._mesh_results_xml, self._u_factor_results_xml = self._builders()
        self._builders = None

    @property
    def mesh_results_xml(self):
        """Serialized ``SteadyStateMeshResults.xml`` member."""
        self._materialize()
        return self._mesh_results_xml

    @property
    def steady_state_results_xml(self):
        """Serialized ``SteadyStateResults.xml`` member."""
        self._materialize()
        return self._u_factor_results_xml

    @property
    def members(self):
        """Output archive member names to bytes, inputs passed through."""
        members = dict(self._members)
        if self._transient is not None:
            for name, path in self._transient['members'].items():
                members[name] = path.read_bytes()
        else:
            self._materialize()
            members['SteadyStateMeshResults.xml'] = self._encode(
                self._mesh_results_xml)
            members['SteadyStateResults.xml'] = self._encode(
                self._u_factor_results_xml)
        members['pyHygroTherm.json'] = json.dumps(
            self.provenance).encode('utf-8')
        return members

    def member_sources(self):
        """Yield ``(member_name, bytes | Path)`` for archive writing.

        Transient series members are returned as paths so ``run_thmz`` can
        stream them into the archive without loading long sequences into
        memory; everything else is bytes.
        """
        for name, content in self._members.items():
            yield name, content
        if self._transient is not None:
            for name, path in self._transient['members'].items():
                yield name, path
        else:
            self._materialize()
            yield 'SteadyStateMeshResults.xml', self._encode(
                self._mesh_results_xml)
            yield 'SteadyStateResults.xml', self._encode(
                self._u_factor_results_xml)
        yield 'pyHygroTherm.json', json.dumps(
            self.provenance).encode('utf-8')

    @staticmethod
    def _encode(value):
        return value.encode('utf-8') if isinstance(value, str) else value

    def __repr__(self):
        return 'SolvedResult(mode={!r}, nodes={})'.format(
            self.mode, len(self.temperatures))
