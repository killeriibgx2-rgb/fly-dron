package com.zzynes.flydrone.entity;

import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

public class FpvDroneModel extends GeoModel<FpvDroneEntity> {

    @Override
    public ResourceLocation getModelResource(FpvDroneEntity object) {
        return new ResourceLocation("fly_drone", "geo/fpv_drone.geo.json");
    }

    @Override
    public ResourceLocation getTextureResource(FpvDroneEntity object) {
        return new ResourceLocation("fly_drone", "textures/entity/fpv_drone.png");
    }

    @Override
    public ResourceLocation getAnimationResource(FpvDroneEntity object) {
        return new ResourceLocation("fly_drone", "animations/fpv_drone.animation.json");
    }
}