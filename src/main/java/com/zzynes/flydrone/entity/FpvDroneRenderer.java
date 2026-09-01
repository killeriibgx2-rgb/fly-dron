package com.zzynes.flydrone.entity;

import com.mojang.blaze3d.vertex.PoseStack;
import com.zzynes.flydrone.FpvOverlay;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

public class FpvDroneRenderer extends GeoEntityRenderer<FpvDroneEntity> {

    public FpvDroneRenderer(EntityRendererProvider.Context renderManager) {
        super(renderManager, new FpvDroneModel());
        this.shadowRadius = 0.0f;
    }

    @Override
    public boolean shouldShowName(FpvDroneEntity entity) {
        return !FpvOverlay.fpvActive;
    }

    @Override
    protected void renderNameTag(FpvDroneEntity entity, Component content, PoseStack poseStack, MultiBufferSource bufferSource, int packedLight) {
        if (FpvOverlay.fpvActive) return;
        super.renderNameTag(entity, Component.literal("HP: " + entity.getDroneHp() + " / 5"), poseStack, bufferSource, packedLight);
    }

    @Override
    public ResourceLocation getTextureLocation(FpvDroneEntity entity) {
        return new ResourceLocation("fly_drone", "textures/entity/fpv_drone.png");
    }
}