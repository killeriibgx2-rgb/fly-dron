package com.zzynes.flydrone.DRONE.entity;

import com.zzynes.flydrone.DRONE.DroneDisconnectPacket;
import com.zzynes.flydrone.DRONE.ModNetwork;
import com.zzynes.flydrone.DRONE.init.ModItems;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;
import org.joml.Quaternionf;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

public class FpvDroneEntity extends PathfinderMob implements GeoEntity {

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    private static final RawAnimation FLY_ANIM = RawAnimation.begin().thenLoop("fly");
    private static final RawAnimation STOP_ANIM = RawAnimation.begin().thenLoop("stop");

    private static final EntityDataAccessor<Float> THROTTLE = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Integer> BATTERY_TICKS = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> MOTOR_TEMP = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> BATTERY_TEMP = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Boolean> IS_FLYING = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DRONE_HP = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> QUAT_X = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> QUAT_Y = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> QUAT_Z = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> QUAT_W = SynchedEntityData.defineId(FpvDroneEntity.class, EntityDataSerializers.FLOAT);

    private float pitchRate = 0f;
    private float rollRate = 0f;
    private float yawRate = 0f;
    private final Quaternionf orientation = new Quaternionf();

    private final Quaternionf renderPrevQuat = new Quaternionf();
    private final Quaternionf renderQuat = new Quaternionf();

    private boolean dead = false;
    private boolean motorLocked = false;
    private UUID controllerUUID = null;
    private int renderDistance = 10;
    private double prevVelY = 0;
    private double prevHoriz = 0;
    private final Set<ChunkPos> loadedChunks = new HashSet<>();
    private ChunkPos lastChunk = null;

    private static final float MAX_THROTTLE = 1.0f;
    private static final float THROTTLE_RAMP_SPEED = 0.9f;
    private static final float ANGULAR_DAMPING = 0.65f;
    private static final float GRAVITY_FORCE = 0.05f;
    private static final float THRUST_FORCE = 0.14f;
    private static final float DRAG = 0.06f;
    private static final float MAX_ANGULAR_RATE = 6.5f;

    public FpvDroneEntity(EntityType<? extends FpvDroneEntity> type, Level level) {
        super(type, level);
        this.setNoGravity(true);
        this.orientation.identity();
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        this.entityData.define(THROTTLE, 0.0f);
        this.entityData.define(BATTERY_TICKS, 4800);
        this.entityData.define(MOTOR_TEMP, 32.0f);
        this.entityData.define(BATTERY_TEMP, 32.0f);
        this.entityData.define(IS_FLYING, false);
        this.entityData.define(DRONE_HP, 5);
        this.entityData.define(QUAT_X, 0f);
        this.entityData.define(QUAT_Y, 0f);
        this.entityData.define(QUAT_Z, 0f);
        this.entityData.define(QUAT_W, 1f);
    }

    @Override
    public void tick() {
        this.prevVelY = this.getDeltaMovement().y;
        this.prevHoriz = Math.sqrt(this.getDeltaMovement().x * this.getDeltaMovement().x + this.getDeltaMovement().z * this.getDeltaMovement().z);

        super.tick();

        if (this.level().isClientSide()) {
            renderPrevQuat.set(renderQuat);
            renderQuat.set(this.entityData.get(QUAT_X), this.entityData.get(QUAT_Y), this.entityData.get(QUAT_Z), this.entityData.get(QUAT_W));
            return;
        }

        ServerLevel sl = (ServerLevel) this.level();

        if (this.controllerUUID != null) {
            updateChunkLoading(sl);
        }

        if (this.isInWater() || this.isInLava()) {
            this.explodeDrone();
            return;
        }

        if (this.verticalCollision && this.prevVelY < -0.45) {
            this.explodeDrone();
            return;
        }

        if (this.horizontalCollision && this.prevHoriz > 0.2) {
            this.explodeDrone();
            return;
        }

        float throttle = this.entityData.get(THROTTLE);

        if (this.onGround()) {
            pitchRate = 0f;
            rollRate = 0f;
            yawRate = 0f;
        } else {
            pitchRate *= ANGULAR_DAMPING;
            rollRate *= ANGULAR_DAMPING;
            yawRate *= ANGULAR_DAMPING;

            pitchRate = Mth.clamp(pitchRate, -MAX_ANGULAR_RATE, MAX_ANGULAR_RATE);
            rollRate = Mth.clamp(rollRate, -MAX_ANGULAR_RATE, MAX_ANGULAR_RATE);
            yawRate = Mth.clamp(yawRate, -MAX_ANGULAR_RATE, MAX_ANGULAR_RATE);

            Quaternionf deltaRotation = new Quaternionf()
                    .rotateX(pitchRate * 0.01745f)
                    .rotateZ(rollRate * 0.01745f)
                    .rotateY(yawRate * 0.01745f);
            orientation.mul(deltaRotation);
            orientation.normalize();
        }

        this.entityData.set(QUAT_X, orientation.x);
        this.entityData.set(QUAT_Y, orientation.y);
        this.entityData.set(QUAT_Z, orientation.z);
        this.entityData.set(QUAT_W, orientation.w);

        Vec3 forward = rotateVec(orientation, 0f, 0f, 1f);
        this.setYRot((float) Math.toDegrees(Math.atan2(-forward.x, forward.z)));
        this.setXRot((float) Math.toDegrees(-Math.asin(Mth.clamp(forward.y, -1.0f, 1.0f))));

        Vec3 up = rotateVec(orientation, 0f, 1f, 0f);
        Vec3 motion = this.getDeltaMovement();

        double ax = up.x * throttle * THRUST_FORCE;
        double ay = up.y * throttle * THRUST_FORCE - GRAVITY_FORCE;
        double az = up.z * throttle * THRUST_FORCE;

        this.setDeltaMovement(
                (motion.x + ax) * (1.0 - DRAG),
                (motion.y + ay) * (1.0 - DRAG),
                (motion.z + az) * (1.0 - DRAG)
        );

        if (throttle > 0.01f) {
            int ticks = this.entityData.get(BATTERY_TICKS);
            ticks -= Math.max(1, (int) (throttle * 3));
            if (ticks < 0) ticks = 0;
            this.entityData.set(BATTERY_TICKS, ticks);

            float motorTemp = this.entityData.get(MOTOR_TEMP);
            motorTemp += throttle * 0.0567f;
            motorTemp = Math.min(motorTemp, 120.0f);
            this.entityData.set(MOTOR_TEMP, motorTemp);

            float battTemp = this.entityData.get(BATTERY_TEMP);
            battTemp += 0.019f * throttle * throttle;
            battTemp = Math.min(battTemp, 120.0f);
            this.entityData.set(BATTERY_TEMP, battTemp);
        } else {
            float motorTemp = this.entityData.get(MOTOR_TEMP);
            motorTemp = Math.max(32.0f, motorTemp - 0.1133f);
            this.entityData.set(MOTOR_TEMP, motorTemp);

            float battTemp = this.entityData.get(BATTERY_TEMP);
            battTemp = Math.max(32.0f, battTemp - 0.038f);
            this.entityData.set(BATTERY_TEMP, battTemp);
        }

        if (this.entityData.get(MOTOR_TEMP) >= 100.0f) {
            this.motorLocked = true;
        }
        if (this.motorLocked && this.entityData.get(MOTOR_TEMP) <= 60.0f) {
            this.motorLocked = false;
        }
        if (this.motorLocked || this.entityData.get(BATTERY_TICKS) <= 0) {
            this.entityData.set(THROTTLE, 0.0f);
        }

        if (this.entityData.get(BATTERY_TEMP) >= 100.0f || this.entityData.get(BATTERY_TICKS) <= 0) {
            this.forceDisconnect();
        }

        if (this.controllerUUID != null && this.level().getServer() != null) {
            ServerPlayer cp = this.level().getServer().getPlayerList().getPlayer(this.controllerUUID);
            if (cp == null) {
                this.forceDisconnect();
            }
        }

        this.entityData.set(IS_FLYING, throttle > 0.01f && this.entityData.get(BATTERY_TICKS) > 0 && !this.motorLocked);
    }

    @Override
    public void checkDespawn() { }

    @Override
    public boolean removeWhenFarAway(double distanceToClosestPlayer) { return false; }

    @Override
    public boolean requiresCustomPersistence() { return true; }

    private void updateChunkLoading(ServerLevel sl) {
        int cx = Mth.floor(this.getX()) >> 4;
        int cz = Mth.floor(this.getZ()) >> 4;
        ChunkPos current = new ChunkPos(cx, cz);

        if (current.equals(this.lastChunk)) return;

        int radius = Math.max(2, this.renderDistance);

        Set<ChunkPos> needed = new HashSet<>();
        for (int dx = -radius; dx <= radius; dx++) {
            for (int dz = -radius; dz <= radius; dz++) {
                needed.add(new ChunkPos(cx + dx, cz + dz));
            }
        }

        for (ChunkPos old : loadedChunks) {
            if (!needed.contains(old)) {
                sl.setChunkForced(old.x, old.z, false);
            }
        }

        for (ChunkPos n : needed) {
            if (!loadedChunks.contains(n)) {
                sl.setChunkForced(n.x, n.z, true);
            }
        }

        loadedChunks.clear();
        loadedChunks.addAll(needed);
        this.lastChunk = current;
    }

    private void stopChunkLoading() {
        if (!(this.level() instanceof ServerLevel sl)) return;
        for (ChunkPos cp : loadedChunks) {
            sl.setChunkForced(cp.x, cp.z, false);
        }
        loadedChunks.clear();
        this.lastChunk = null;
    }

    @Override
    public void remove(Entity.RemovalReason reason) {
        stopChunkLoading();
        super.remove(reason);
    }

    public void setController(UUID uuid) {
        this.controllerUUID = uuid;
    }

    public void setRenderDistance(int rd) {
        this.renderDistance = Math.max(2, Math.min(32, rd));
    }

    private void forceDisconnect() {
        if (this.controllerUUID == null) return;
        UUID id = this.controllerUUID;
        this.controllerUUID = null;
        this.entityData.set(THROTTLE, 0.0f);
        stopChunkLoading();
        if (this.level().getServer() != null) {
            ServerPlayer cp = this.level().getServer().getPlayerList().getPlayer(id);
            if (cp != null) {
                for (InteractionHand hand : InteractionHand.values()) {
                    ItemStack st = cp.getItemInHand(hand);
                    if (st.getItem() == ModItems.REMOTE_CONNECTED.get()) {
                        cp.setItemInHand(hand, new ItemStack(ModItems.REMOTE_DISCONNECTED.get()));
                    }
                }
                ModNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> cp), new DroneDisconnectPacket(this.getUUID()));
            }
        }
    }

    public void explodeDrone() {
        if (this.dead || this.level().isClientSide()) return;
        this.dead = true;
        this.forceDisconnect();
        this.level().explode(this, null, null, this.getX(), this.getY(), this.getZ(), 4.0F, false, Level.ExplosionInteraction.NONE);
        this.discard();
    }

    @Override
    public boolean hurt(DamageSource source, float amount) {
        if (this.level().isClientSide() || this.dead) return false;
        if (this.invulnerableTime > 0) return false;
        this.invulnerableTime = 10;
        int hp = this.entityData.get(DRONE_HP) - Math.max(1, (int) Math.ceil(amount));
        if (hp <= 0) {
            this.entityData.set(DRONE_HP, 0);
            this.explodeDrone();
        } else {
            this.entityData.set(DRONE_HP, hp);
        }
        return true;
    }

    @Override
    public boolean causeFallDamage(float fallDistance, float multiplier, DamageSource source) {
        return false;
    }

    @Override
    public boolean isPushable() { return false; }

    @Override
    public boolean canBeCollidedWith() { return false; }

    @Override
    public boolean isPickable() { return true; }

    @Override
    public void push(Entity entity) { }

    private Vec3 rotateVec(Quaternionf q, float x, float y, float z) {
        float qx = q.x, qy = q.y, qz = q.z, qw = q.w;
        float tx = 2 * (qy * z - qz * y);
        float ty = 2 * (qz * x - qx * z);
        float tz = 2 * (qx * y - qy * x);
        float rx = x + qw * tx + (qy * tz - qz * ty);
        float ry = y + qw * ty + (qz * tx - qx * tz);
        float rz = z + qw * tz + (qx * ty - qy * tx);
        return new Vec3(rx, ry, rz);
    }

    public Quaternionf getInterpolatedOrientation(float partialTick) {
        if (!this.level().isClientSide()) return this.orientation;
        return new Quaternionf(renderPrevQuat).slerp(renderQuat, partialTick);
    }

    @Override
    public void travel(Vec3 travelVector) {
        if (this.isControlledByLocalInstance()) {
            this.move(MoverType.SELF, this.getDeltaMovement());
        }
    }

    public void setThrottle(float value) {
        float current = this.entityData.get(THROTTLE);
        float target = Mth.clamp(value, 0f, MAX_THROTTLE);
        float newThrottle = Mth.lerp(THROTTLE_RAMP_SPEED, current, target);
        this.entityData.set(THROTTLE, newThrottle);
    }

    public void addPitchRate(float rate) { this.pitchRate += rate; }
    public void addRollRate(float rate) { this.rollRate += rate; }
    public void addYawRate(float rate) { this.yawRate += rate; }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "drone_controller", 0, this::animController));
    }

    private <E extends FpvDroneEntity> PlayState animController(AnimationState<E> state) {
        if (!this.onGround() || this.entityData.get(THROTTLE) > 0.01f) {
            return state.setAndContinue(FLY_ANIM);
        }
        return state.setAndContinue(STOP_ANIM);
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        this.entityData.set(BATTERY_TICKS, tag.getInt("BatteryTicks"));
        this.entityData.set(MOTOR_TEMP, tag.getFloat("MotorTemp"));
        this.entityData.set(BATTERY_TEMP, tag.getFloat("BatteryTemp"));
        this.pitchRate = tag.getFloat("PitchRate");
        this.rollRate = tag.getFloat("RollRate");
        this.yawRate = tag.getFloat("YawRate");
        int hp = tag.getInt("DroneHp");
        this.entityData.set(DRONE_HP, hp <= 0 ? 5 : hp);
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        tag.putInt("BatteryTicks", this.entityData.get(BATTERY_TICKS));
        tag.putFloat("MotorTemp", this.entityData.get(MOTOR_TEMP));
        tag.putFloat("BatteryTemp", this.entityData.get(BATTERY_TEMP));
        tag.putFloat("PitchRate", this.pitchRate);
        tag.putFloat("RollRate", this.rollRate);
        tag.putFloat("YawRate", this.yawRate);
        tag.putInt("DroneHp", this.entityData.get(DRONE_HP));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return this.cache;
    }

    public int getDroneHp() { return Math.max(0, this.entityData.get(DRONE_HP)); }
    public float getThrottle() { return this.entityData.get(THROTTLE); }
    public int getBatteryTicks() { return this.entityData.get(BATTERY_TICKS); }
    public float getMotorTemp() { return this.entityData.get(MOTOR_TEMP); }
    public float getBatteryTemp() { return this.entityData.get(BATTERY_TEMP); }
    public boolean isFlying() { return this.entityData.get(IS_FLYING); }
    public Quaternionf getOrientation() { return this.orientation; }
    public UUID getControllerUUID() { return this.controllerUUID; }
}