# ARCHITECTURE

Production game:
Assets/OnlyVolunteers/

Reusable code area (legacy Friendslop networking retired):
Assets/Friendslop/

Active game networking: `Assets/OnlyVolunteers/Network/` uses FishNet/Tugboat. The owner runs the accepted KCC; the server owns shared Rigidbody simulation and exclusive grab holder state. Local and network grab paths share `Assets/OnlyVolunteers/Player/GrabPhysicsProfile.asset` and the network-independent `GrabPhysicsSolver`. The Player and NetworkPlayer roots are separate prefabs, although both nest the same KCC ExampleCharacter prefab.

Prototype/reference only:
Assets/PhysicsInteractionPlayground/

Architecture is still evolving.
Do not invent or assume systems that do not exist yet.
