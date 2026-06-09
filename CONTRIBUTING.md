# Contributing to Lethe

Thanks for your interest in improving Lethe! Contributions — bug reports, fixes,
features, and docs — are welcome.

## License of contributions

Lethe is licensed under the **Apache License, Version 2.0** (Apache-2.0). By
submitting a contribution (a pull request, patch, or any code or content), you
agree that your contribution is licensed under those same Apache-2.0 terms —
**inbound = outbound** — as set out in section 5 of the license. You keep the
copyright to your work; you grant the project and its users the copyright and
patent licenses described in the Apache License.

## Developer Certificate of Origin (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/) —
a lightweight statement that you have the right to submit your contribution under
the project's license.

**Every commit must be signed off.** Git adds the sign-off for you with `-s`:

```
git commit -s -m "Restore multi-word tokens spanning a line break"
```

This appends a line using your real name and email:

```
Signed-off-by: Jane Doe <jane@example.com>
```

By signing off, you certify the DCO (full text below). Pull requests whose
commits lack a `Signed-off-by` line cannot be merged. If you forgot, you can
amend the last commit with `git commit --amend -s`, or rebase to sign off a
series.

## How to contribute

1. Fork the repository and create a topic branch.
2. Make your change; keep it focused and match the surrounding code style.
3. Run the smoke tests where applicable (`tests/test_smoke.py`, `tests/test_doc.py`).
4. Commit with `-s` (DCO sign-off) and open a pull request that explains the
   change and why.

## Developer Certificate of Origin 1.1

```
By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have the right
    to submit it under the open source license indicated in the file; or

(b) The contribution is based upon previous work that, to the best of my
    knowledge, is covered under an appropriate open source license and I have
    the right under that license to submit that work with modifications,
    whether created in whole or in part by me, under the same open source
    license (unless I am permitted to submit under a different license), as
    indicated in the file; or

(c) The contribution was provided directly to me by some other person who
    certified (a), (b) or (c) and I have not modified it.

(d) I understand and agree that this project and the contribution are public and
    that a record of the contribution (including all personal information I
    submit with it, including my sign-off) is maintained indefinitely and may be
    redistributed consistent with this project or the open source license(s)
    involved.
```
