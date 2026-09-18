# OpenKCC adaptation

`OnlyVolunteersCapsuleMotor.cs` adapts the capsule-cast and iterative collision-plane
projection architecture from OpenKCC:

- Repository: https://github.com/nicholas-maltbie/OpenKCC
- Source files studied/adapted: `KCCUtils.cs`, `CapsuleColliderCast.cs`,
  `AbstractPrimitiveColliderCast.cs`, and `KCCMovementEngine.cs`
- Upstream revision studied: `a1a30ed7f7722ea82a1df6bd01849e0bfde6abf4`

The adaptation is intentionally scoped to the Only Volunteers player and does not claim
API or behavioral compatibility with the complete OpenKCC package.

## MIT License

Copyright (C) 2023 Nicholas Maltbie

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
