// Made with Blockbench 5.1.5
// Exported for Minecraft version 1.17 or later with Mojang mappings
// Paste this class into your mod and generate all required imports


public class ci4<T extends Entity> extends EntityModel<T> {
	// This layer location should be baked with EntityRendererProvider.Context in the entity renderer and passed into this model's constructor
	public static final ModelLayerLocation LAYER_LOCATION = new ModelLayerLocation(new ResourceLocation("modid", "ci4"), "main");
	private final ModelPart bone;

	public ci4(ModelPart root) {
		this.bone = root.getChild("bone");
	}

	public static LayerDefinition createBodyLayer() {
		MeshDefinition meshdefinition = new MeshDefinition();
		PartDefinition partdefinition = meshdefinition.getRoot();

		PartDefinition bone = partdefinition.addOrReplaceChild("bone", CubeListBuilder.create().texOffs(48, 0).addBox(2.0F, 1.0F, -7.0F, 2.0F, 2.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(0, 69).addBox(2.0F, -2.0F, -7.0F, 2.0F, 2.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(0, 51).addBox(-4.0F, 1.0F, -7.0F, 2.0F, 2.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(72, 51).addBox(-4.0F, -2.0F, -7.0F, 2.0F, 2.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(36, 51).addBox(-1.0F, 1.0F, -7.0F, 2.0F, 2.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(36, 69).addBox(-1.0F, -2.0F, -7.0F, 2.0F, 2.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(58, 30).addBox(1.0F, 1.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(70, 30).addBox(1.0F, -1.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(60, 32).addBox(-2.0F, 1.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(72, 32).addBox(-2.0F, -1.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(62, 26).addBox(1.0F, 1.5F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(70, 28).addBox(1.0F, -1.5F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(62, 30).addBox(2.5F, 0.0F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(64, 32).addBox(-0.5F, 0.0F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(66, 26).addBox(-3.5F, 0.0F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(66, 28).addBox(-3.5F, 0.0F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(66, 30).addBox(-0.5F, 0.0F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(68, 32).addBox(2.5F, 0.0F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(62, 28).addBox(-2.0F, 1.5F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(70, 26).addBox(-2.0F, -1.5F, 7.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(0, 0).addBox(-4.0F, -3.0F, -7.0F, 8.0F, 1.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(0, 17).addBox(-4.0F, 3.0F, -7.0F, 8.0F, 1.0F, 16.0F, new CubeDeformation(0.0F))
		.texOffs(48, 18).addBox(-4.0F, -4.0F, -7.0F, 8.0F, 1.0F, 7.0F, new CubeDeformation(0.0F))
		.texOffs(72, 69).addBox(2.0F, -4.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(72, 71).addBox(0.5F, -4.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(74, 26).addBox(-1.5F, -4.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(74, 28).addBox(-0.5F, -4.5F, -4.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(58, 26).addBox(-1.6F, -4.5F, -4.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(58, 28).addBox(-2.7F, -4.5F, -4.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(48, 32).addBox(-2.7F, -4.5F, -2.9F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(54, 26).addBox(-1.6F, -4.5F, -2.9F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(54, 28).addBox(-0.5F, -4.5F, -2.9F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(56, 32).addBox(-0.5F, -4.5F, -1.8F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(54, 30).addBox(-1.6F, -4.5F, -1.8F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(52, 32).addBox(-2.7F, -4.5F, -1.8F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(48, 26).addBox(4.5F, -3.5F, -7.0F, 1.0F, 1.0F, 2.0F, new CubeDeformation(0.0F))
		.texOffs(2, 1).addBox(2.5F, -3.5F, -7.5F, 1.0F, 3.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(48, 29).addBox(2.5F, -4.5F, -3.0F, 1.0F, 1.0F, 2.0F, new CubeDeformation(0.0F))
		.texOffs(72, 73).addBox(-3.0F, -4.5F, -6.0F, 1.0F, 1.0F, 1.0F, new CubeDeformation(0.0F))
		.texOffs(2, 1).addBox(-3.5F, -3.5F, -7.5F, 1.0F, 3.0F, 1.0F, new CubeDeformation(0.0F)), PartPose.offset(0.0F, 21.0F, -1.0F));

		PartDefinition cube_r1 = bone.addOrReplaceChild("cube_r1", CubeListBuilder.create().texOffs(46, 34).addBox(-2.0F, -1.0F, -8.0F, 7.0F, 1.0F, 16.0F, new CubeDeformation(0.0F)), PartPose.offsetAndRotation(-5.0F, -1.0F, 1.0F, 0.0F, 0.0F, 1.5708F));

		PartDefinition cube_r2 = bone.addOrReplaceChild("cube_r2", CubeListBuilder.create().texOffs(0, 34).addBox(-2.0F, -1.0F, -8.0F, 7.0F, 1.0F, 16.0F, new CubeDeformation(0.0F)), PartPose.offsetAndRotation(4.0F, -1.0F, 1.0F, 0.0F, 0.0F, 1.5708F));

		return LayerDefinition.create(meshdefinition, 128, 128);
	}

	@Override
	public void setupAnim(Entity entity, float limbSwing, float limbSwingAmount, float ageInTicks, float netHeadYaw, float headPitch) {

	}

	@Override
	public void renderToBuffer(PoseStack poseStack, VertexConsumer vertexConsumer, int packedLight, int packedOverlay, float red, float green, float blue, float alpha) {
		bone.render(poseStack, vertexConsumer, packedLight, packedOverlay, red, green, blue, alpha);
	}
}